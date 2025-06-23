import base64
import multiprocessing
import os
import socket
import threading
import time
import typing
from copy import copy
from itertools import count
from typing import Optional

import zmq
from tornado.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from neurpi.loggers.logger import init_logger
from neurpi.networking.message import Message
from neurpi.prefs import prefs


class Station(multiprocessing.Process):
    """
    Args:

    Attributes:
        id (str): Current node id
        ip (str): Device IP
        context: zeromq context
        loop: tornado ioloop
        # DEALER socker
        pusher: dealer socket that connects to other routers
        push_id (str): If we have dealer, identity of ROUTER conneting with dealer
        push_ip (str): If we have dealer, IP address to push message to
        push_port (str): If we have dealer, port number to push message to
        # ROUTER socker
        listener (zmq socket): Main router socket to sent/receive messages
        listen_port (str): port router listens to

        listens (dict): Dictionary of functions to call for different types of messages.
        senders (dict): Identities of other sockets (keys, i.e., directly connected and their state (values) if they keep one)

        push_outbox (dict):
        send_outbox (dict):

        msg_counter: counter to index sent messages
        file_block: Threading event to register when a file is being received.

    """

    repeat_interval = 5.0  # seconds to wait before retrying messages

    def __init__(
        self,
        id: Optional[str] = None,
        pusher: bool = False,
        push_id: Optional[str] = None,
        push_ip: Optional[str] = None,
        push_port: Optional[str] = None,
        listen_port: Optional[int] = None,
        listens: Optional[typing.Dict[str, typing.Callable]] = None,
    ):
        super(Station, self).__init__()
        self.id = id
        self.context = None
        self.loop = None

        self.pusher = pusher  # type: Union[bool, zmq.Socket]
        self.push_ip = push_ip
        self.push_port = push_port
        self.push_id = push_id.encode("utf-8") if isinstance(push_id, str) else push_id

        self.listener = None
        self.listen_port = listen_port

        self.push_outbox = {}
        self.send_outbox = {}

        self.repeat_thread = None
        self.senders = {}
        self.timers = {}
        self.child = False
        self.routes = {}
        self.msgs_received = multiprocessing.Value("i", lock=True)
        self.msgs_received.value = 0

        try:
            self.ip = self.get_ip()
        except Exception as e:
            Warning(f"Couldn't get IP: {e}")
            self.ip = ""

        self.file_block = multiprocessing.Event()  # to wait for file transfer

        # Count and number messages as we send them
        self.msg_counter = count()

        # Few built-in listens
        if listens is None:
            listens = {}
        self.listens = listens
        self.listens.update(
            {"CONFIRM": self.l_confirm, "STREAM": self.l_stream, "KILL": self.l_kill},
        )

        # closing event signal
        self.closing = multiprocessing.Event()
        self.closing.clear()

    def __del__(self):
        try:
            self.release()
        except:
            pass

    def get_ip(self):
        """
        Find our IP address using a more reliable and understandable method.

        Returns:
            str: Our IPv4 address.

        """
        try:
            # Method 1: Connect to a public DNS server to determine the local IP
            # This doesn't actually send data, just determines routing
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to Google's public DNS (doesn't send data)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                return local_ip
        except Exception:
            # Method 2: Fallback to hostname resolution
            try:
                # Get all IP addresses associated with this hostname
                hostname = socket.gethostname()
                ip_list = socket.gethostbyname_ex(hostname)[2]

                # Filter out loopback addresses and select first valid IP
                for ip in ip_list:
                    if not ip.startswith("127.") and not ip.startswith("::1"):
                        return ip

                # If no valid IP found, return localhost
                return "127.0.0.1"
            except Exception:
                # Final fallback
                return "127.0.0.1"

    def prepare_message(self, to, key, value, repeat=True, flags=None):
        """
        If a message originates with this node, a message class is instantiated and given an ID and other attributes

        Args:
            flags:
            repeat:
            to (str): Identity of receiving socket
            key (str): Type of message - indicating which process receiver should use to process the message
            value: Massesge, must be in JSON serializable format

        """
        msg = Message()
        msg.sender = self.id
        msg.value = value
        try:
            msg.to = to.decode("utf-8")
        except AttributeError:
            msg.to = to

        try:
            msg.key = key.decode("utf-8")
        except AttributeError:
            msg.key = key

        msg_num = next(self.msg_counter)
        msg.id = f"{self.id}_{msg_num}"

        if not repeat:
            msg.flags["NOREPEAT"] = True

        if flags:
            for k, v in flags.items():
                msg.flags[k] = v

        return msg

    def send(self, to=None, key=None, value=None, msg=None, repeat=True, flags=None):
        """
        Send a message via Router socket.
        If Message is not already prepared as msg, at least `to` and `key` must be provided.

        A `threading.Timer` is created to resent the message using `self.repeat` method if requested.

        Args:
            flags:
            to (str): identity of receiving socket
            key (str): Type of message - indicating which process receiver should use to process the message
            value: Massesge, must be in JSON serializable format
            msg: prepared message
            repeat (bool): Should we resend this message if confirmation not received?

        """
        if not msg and not all([to, key]):
            self.logger.exception(
                f"Need either a message or 'to' and 'key' fields.\
                Got\nto: {to}\nkey: {key}\nvalue: {value}\nmsg: {msg}",
            )
            return

        manual_to = False
        if not msg:
            msg = self.prepare_message(to, key, value, repeat, flags)
        elif to:
            # if both prepared_message and `to` is provided, send it to original to
            manual_to = True

        if "NOREPEAT" in msg.flags.keys():
            repeat = False

        # If msg didn't originate with this node, no need to double-confirm.
        if msg.sender not in [self.name, "_" + self.name]:
            repeat = False

        # Make sure msg has all required fields
        if not msg.validate():
            self.logger.exception(f"Message Invalid:\n{msg!s}")

        # Encode message
        msg_enc = msg.serialize()

        if not msg_enc:
            self.logger.exception(f"Message could not be encoded:\n{msg!s}")
            return

        if manual_to:
            self.listener.send_multipart([to.encode("utf-8"), msg_enc])
        elif isinstance(msg.to, list):
            self.listener.send_multipart(
                [*[hop.encode("utf-8") for hop in to], msg_enc],
            )
        else:
            self.listener.send_multipart([msg.to.encode("utf-8"), msg_enc])

        self.logger.debug(f"MESSAGE SENT - {msg!s}")

        if repeat and not msg.key == "CONFIRM":
            # add to outbox and spawn timer to resend
            self.send_outbox[msg.id] = (time.time(), msg)

    def push(self, to=None, key=None, value=None, msg=None, repeat=True, flags=None):
        """
        Send a message via Dealer socket.
        If Message is not already prepared as msg, at least `to` and `key` must be provided.

        A `threading.Timer` is created to resent the message using `self.repeat` method if requested.

        Args:
            flags:
            to (str): identity of receiving socket
            key (str): Type of message - indicating which process receiver should use to process the message
            value: Massesge, must be in JSON serializable format
            msg: prepared message
            repeat (bool): Should we resend this message if confirmation not received?

        """
        if not msg and not all([to, key]):
            self.logger.exception(
                f"Need either a message or 'to' and 'key' fields.\
                Got\nto: {to}\nkey: {key}\nvalue: {value}\nmsg: {msg}",
            )
            return

        if not msg:
            if to is None:
                to = self.push_id
            msg = self.prepare_message(to, key, value, repeat, flags)

        if "NOREPEAT" in msg.flags.keys():
            repeat = False

        log_this = True
        if "NOLOG" in msg.flags.keys():
            log_this = False

        # Make sure msg has all required fields
        if not msg.validate():
            self.logger.exception(f"Message Invalid:\n{msg!s}")

        # Encode message
        msg_enc = msg.serialize()

        if not msg_enc:
            self.logger.exception(f"Message could not be encoded:\n{msg!s}")
            return

        # Even if the message is not to our upstream node, we still send it
        # upstream because presumably our target is upstream.
        self.pusher.send_multipart(
            [self.push_id, bytes(msg.to, encoding="utf-8"), msg_enc],
        )

        if not (msg.key == "CONFIRM") and log_this:
            self.logger.debug(f"MESSAGE PUSHED - {msg!s}")

        if repeat and not msg.key == "CONFIRM":
            # add to outbox and spawn timer to resend
            self.push_outbox[msg.id] = (time.time(), msg)

    def l_confirm(self, msg):
        """
        Confirm that message was received.

        Args:
            msg(:class:`.Message`): A confirmation message with it's unique ID. The value of the message contains the ID of the message that is being confirmed

        """
        # value should be the id of message to be confirmed

        # delete message from outbox if we still havbe it
        try:
            if msg.value in self.send_outbox.keys():
                del self.send_outbox[msg.value]
            elif msg.value in self.push_outbox.keys():
                del self.push_outbox[msg.value]
        except KeyError:
            pass

        # if this is a message to our internal net_node, make sure it gets the memo that it was confirmed too
        if msg.to == f"_{self.id}":
            self.send(f"_{self.id}", "CONFIRM", msg.value)

    def l_stream(self, msg):
        """
        Reconstitute the original stream of messages and call their handling methods
        The ``msg`` should contain an ``inner_key`` that indicates the key, and thus the
        handling method.

        Args:
            msg (dict): Compressed stream sent by :meth:`Net_Node._stream`

        """
        listen_fn = self.listens[msg.value["inner_key"]]
        old_value = copy(msg.value)
        delattr(msg, "value")
        msg.key = old_value["inner_key"]
        for v in old_value["payload"]:
            if isinstance(v, dict) and ("headers" in old_value.keys()):
                v.update(old_value["headers"])
            msg.value = v
            listen_fn(msg)

    def l_kill(self, msg: Message):
        """
        Controller wants us to die :(
        Stop the :attr:`.Station.loop`
        Args:
            msg (:class:`.Message`):
        """
        self.logger.info("Received kill request")
        self.closing.set()

        # First close the sockets properly
        try:
            if self.listener:
                self.listener.stop_on_recv()
                self.listener.close()

            if self.pusher and hasattr(self.pusher, "close"):
                self.pusher.stop_on_recv()
                self.pusher.close()

            # Close the underlying ZMQ sockets
            if hasattr(self, "context") and self.context:
                # Terminate all sockets in the context
                self.context.term()

        except Exception as e:
            self.logger.error(f"Error closing sockets: {e}")

        # Stop the IOLoop
        try:
            if self.loop:
                self.loop.add_callback(lambda: IOLoop.instance().stop())
                self.logger.debug(self.loop)
        except Exception as e:
            self.logger.error(f"Error stopping IOLoop: {e}")

        self.logger.info("Stopped IOLoop")

    def release(self):
        """Enhanced release method with robust cleanup"""
        self.closing.set()

        try:
            # First try graceful shutdown by sending CLOSING message to ourselves
            ctx = zmq.Context().instance()
            sock = ctx.socket(zmq.DEALER)
            sock.setsockopt_string(zmq.IDENTITY, f"{self.id}/closer")
            sock.setsockopt(zmq.LINGER, 0)  # Don't wait for pending messages

            try:
                sock.connect(f"tcp://localhost:{self.listen_port}")
                sock.send_multipart([self.id.encode("utf-8"), b"CLOSING"])
                self.logger.debug("Sent CLOSING message to self")
            except zmq.ZMQError as e:
                self.logger.warning(f"Failed to send CLOSING message: {e}")
            finally:
                sock.close()

            # Give the process a moment to close gracefully
            time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")

        finally:
            # Force termination if still alive
            if self.is_alive():
                self.logger.warning("Process still alive, forcing termination")
                self.terminate()

                # Wait a bit then force kill if necessary
                time.sleep(0.5)
                if self.is_alive():
                    self.logger.warning("Process still alive after terminate, using kill")
                    self.kill()

    def _check_stop(self):
        """
        Periodic callback called by the IOLoop to check if the closing flag has been set and if set, close the process
        """
        if self.closing.is_set():
            self.loop.stop()

    def repeat(self):
        """
        Periodically resend messages that haven't been confirmed.

        Decrementing TTL based counter.
        """
        while not self.closing.is_set():
            # make local copies
            send_outbox = copy(self.send_outbox)
            push_outbox = copy(self.push_outbox)

            # try to send outstanding messages and delete if too old
            if len(push_outbox) > 0:
                for id in push_outbox.keys():
                    if push_outbox[id][1].ttl <= 0:
                        self.logger.warning(
                            f"PUBLISH FAILED {id} - {push_outbox[id][1]!s}",
                        )
                        try:
                            del self.push_outbox[id]
                        except KeyError:
                            # fine, already deleted
                            pass
                    # if we didn't just put this message in our outbox
                    elif (time.time() - push_outbox[id][0]) > self.repeat_interval * 2:
                        self.logger.debug(f"REPUBLISH {id} - {push_outbox[id][1]!s}")
                        self.pusher.send_multipart(
                            [self.push_id, push_outbox[id][1].serialize()],
                        )
                        self.push_outbox[id][1].ttl -= 1

            if len(send_outbox) > 0:
                for id in send_outbox.keys():
                    if send_outbox[id][1].ttl <= 0:
                        self.logger.warning(
                            f"PUBLISH FAILED {id} - {send_outbox[id][1]!s}",
                        )
                        try:
                            del self.send_outbox[id]
                        except KeyError:
                            # fine, already deleted
                            pass

                    # if we didn't just put this message in our outbox
                    elif (time.time() - send_outbox[id][0]) > self.repeat_interval * 2:
                        self.logger.debug(f"REPUBLISH {id} - {send_outbox[id][1]!s}")
                        self.listener.send_multipart(
                            [
                                bytes(send_outbox[id][1].to, encoding="utf-8"),
                                send_outbox[id][1].serialize(),
                            ],
                        )
                        self.send_outbox[id][1].ttl -= 1  # wait to do it again
            time.sleep(self.repeat_interval)

    def run(self):
        """
        A :class:`zmq.Context` and :class:`tornado.IOLoop` are spawned,
        the listener and optionally the pusher are instantiated and
        connected to :meth:`~.Station.handle_listen` using
        :meth:`~zmq.eventloop.zmqstream.ZMQStream.on_recv` .
        The process is kept open by the :class:`tornado.IOLoop` .
        """
        try:
            # Configure preferences for this process - determine mode based on station type
            from neurpi.prefs import configure_prefs

            if "Controller" in self.__class__.__name__:
                configure_prefs("controller")
            elif "Rig" in self.__class__.__name__:
                configure_prefs("rig")
            else:
                # Default to controller mode
                configure_prefs("controller")

            self.logger = init_logger(self)
            # init zmq objects
            self.context = zmq.Context()
            self.loop = IOLoop()

            # Our networking topology is treelike:
            # each Station object binds one Router to
            # send and receive messages from its descendants
            # each Station object may have one Dealer that
            # connects it with its antecedents.
            self.listener = self.context.socket(zmq.ROUTER)
            self.listener.setsockopt_string(zmq.IDENTITY, self.id)

            # Enable socket reuse to handle crashes more gracefully
            self.listener.setsockopt(zmq.LINGER, 0)  # Don't wait for pending messages

            try:
                self.listener.bind(f"tcp://*:{self.listen_port}")
            except zmq.ZMQError as e:
                if "Address already in use" in str(e):
                    self.logger.warning(f"Port {self.listen_port} already in use, waiting and retrying...")
                    time.sleep(1.0)  # Wait for previous instance to cleanup
                    try:
                        self.listener.bind(f"tcp://*:{self.listen_port}")
                    except zmq.ZMQError:
                        self.logger.error(f"Failed to bind to port {self.listen_port} after retry")
                        raise
                else:
                    raise
            self.listener = ZMQStream(self.listener, self.loop)
            self.listener.on_recv(self.handle_listen)

            if self.pusher is True:
                self.pusher = self.context.socket(zmq.DEALER)
                self.pusher.setsockopt_string(zmq.IDENTITY, self.id)
                self.pusher.connect(f"tcp://{self.push_ip}:{self.push_port}")
                self.pusher = ZMQStream(self.pusher, self.loop)
                self.pusher.on_recv(self.handle_listen)
                # TODO: Make sure handle_listen knows how to handle ID-less messages

            # start thread that periodically resends messages
            self.repeat_thread = threading.Thread(target=self.repeat)
            self.repeat_thread.setDaemon(True)
            self.repeat_thread.start()

            self.logger.info("Starting IOLoop")
            self.loop.start()
        except KeyboardInterrupt:
            # normal quitting behavior
            self.logger.debug("Stopped with KeyboardInterrupt")
        finally:
            self.context.destroy()
            self.loop.close()
            self.logger.debug("Reached finally, closing Station")
            # self.release()

    def handle_listen(self, msg: typing.List[bytes]):
        """
        Upon receiving a message, call the appropriate listen method
        in a new thread.

        If the message is :attr:`~.Message.to` us, send confirmation.

        If the message is not :attr:`~.Message.to` us, attempt to forward it.

        Args:
            msg (str): JSON :meth:`.Message.serialize` d message.

        """
        # TODO: This check is v. fragile, pyzmq has a way of sending the stream along with the message
        #####################33
        # Parse the message
        with self.msgs_received.get_lock():
            self.msgs_received.value += 1

        if msg[-1] == b"CLOSING":
            self.loop.stop()

        if len(msg) == 1:
            # from our dealer, these are always to us.
            send_type = "dealer"
            # msg = json.loads(msg[0])
            # msg = Message(**msg)
            msg = Message(msg[0])

        elif len(msg) >= 2:
            # from the router
            send_type = "router"
            sender = msg[0]

            # if this message was a multihop message, store the route
            if len(msg) > 4:
                self.routes[sender] = msg[0:-3]

            # # if this is a new sender, add them to the list
            if sender not in self.senders.keys():
                self.senders[sender] = ""
                self.senders[b"_" + sender] = ""

            # connection pings are blank frames,
            # respond to let them know we're alive
            if msg[-1] == b"":
                self.listener.send_multipart(msg)
                return

            # if this message wasn't to us, forward without deserializing
            # the second to last should always be the intended recipient
            unserialized_to = msg[-2]
            if unserialized_to.decode("utf-8") not in [self.id, f"_{self.id}"]:
                # forward it!
                if len(msg) > 4:
                    # multihop message, just determine whether the next hop is through
                    # our pusher or router
                    if self.pusher and msg[2] not in self.senders.keys():
                        self.pusher.send_multipart(msg[2:])
                        self.logger.debug(f"FORWARDING (multihop dealer): {msg}")
                    else:
                        self.listener.send_multipart(msg[2:])
                        self.logger.debug(f"FORWARDING (multihop router): {msg}")
                elif unserialized_to not in self.senders.keys() and self.pusher:
                    # if we don't know who they are and we have a pusher, try to push it
                    self.pusher.send_multipart([self.push_id, *msg[2:]])
                    self.logger.debug(f"FORWARDING (dealer): {msg}")
                else:
                    # if we know who they are or not, try to send it through router anyway.
                    # send everything but the first two frames, which should be the ID of
                    # the sender and us
                    self.listener.send_multipart(msg[2:])
                    self.logger.debug(f"FORWARDING (router): {msg}")

                return

            msg = Message(msg[-1])

            # if this is a new sender, add them to the list
            if msg["sender"] not in self.senders.keys():
                self.senders[msg["sender"]] = ""
                self.senders["_" + msg["sender"]] = ""

        else:
            self.logger.error(f"Dont know what this message is:{msg}")
            return

        ###################################
        # Handle the message

        # unstack and listed to fields remaining from forwarding
        if isinstance(msg.to, list):
            if len(msg.to) == 1:
                msg.to = msg.to[0]

        # if this message is to us, just handle it and return
        if msg.to in [self.id, f"_{self.id}"]:
            if msg.key != "CONFIRM":
                self.logger.debug(f"RECEIVED: {msg!s}")
            # Log and spawn thread to respond to listen
            try:
                listen_funk = self.listens[msg.key]
                listen_thread = threading.Thread(target=listen_funk, args=(msg,))
                listen_thread.start()
            except KeyError:
                self.logger.exception(
                    f"No function could be found for msg id {msg.id} with key: {msg.key}",
                )

            # send a return message that confirms even if we except
            # don't confirm confirmations
            if (msg.key != "CONFIRM") and ("NOREPEAT" not in msg.flags.keys()):
                if send_type == "router":
                    self.send(msg.sender, "CONFIRM", msg.id)
                elif send_type == "dealer":
                    self.push(msg.sender, "CONFIRM", msg.id)
            return
        if self.child and (msg.to == "T"):
            # FIXME UGLY HACK
            self.push(msg=msg)
        else:
            self.logger.exception(
                f"Message not to us, but wasnt forwarded previously in handling method, message must be misformatted: {msg}",
            )


class ControllerStation(Station):
    """
    class obj for master computer inheriting networking.Station.

    Spawned without a `Station.pusher` attribute since it's a controller node on the network.


    **Listens**
    +-------------+-------------------------------------------+-----------------------------------------------+
    | Key         | Method                                    | Description                                   |
    +=============+===========================================+===============================================+
    | 'PING'      | :meth:`~.ControllerStation.l_ping`         | We are asked to confirm that we are alive     |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'INIT'      | :meth:`~.ControllerStation.l_init`         | Ask all rigs to confirm that they are alive |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'CHANGE'    | :meth:`~.ControllerStation.l_change`       | Change a parameter on the Pi                  |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'STOPALL'   | :meth:`~.ControllerStation.l_stopall`      | Stop all rigs and plots                     |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'KILL'      | :meth:`~.ControllerStation.l_kill`         | Controller wants us to die :(                   |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'DATA'      | :meth:`~.ControllerStation.l_data`         | Stash incoming data from a rig              |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'STATE'     | :meth:`~.ControllerStation.l_state`        | A rig has changed state                     |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'HANDSHAKE' | :meth:`~.ControllerStation.l_handshake`    | A Pi is telling us it's alive and its IP      |
    +-------------+-------------------------------------------+-----------------------------------------------+
    | 'FILE'      | :meth:`~.ControllerStation.l_file`         | The pi needs some file from us                |
    +-------------+-------------------------------------------+-----------------------------------------------+

    """

    plot_timer = None

    # dict of threading events that determines how frequently we sent plot updates
    sent_plot = {}

    def __init__(self, rigs):
        """
        Args:
            rigs (dict): All node rig dictionary

        """
        super(ControllerStation, self).__init__()

        # by default controller doesn't have a pusher, since it's a end tree node and everything connects to it
        self.pusher = False

        self.listen_port = prefs.get("MSGPORT")
        self.id = "T"

        # message dictionary - what method to call for each typr of message received by the controller class
        self.listens.update(
            {
                "PING": self.l_ping,  # We are asked to confirm that we are alive
                "INIT": self.l_init,  # We should ask all the rigs to confirm that they are alive
                "CHANGE": self.l_change,  # Change a parameter on the Pi
                "STOPALL": self.l_stopall,  # Stop all rigs and plots
                "DATA": self.l_data,  # Stash incoming data from an autorig
                "CONTINUOUS": self.l_continuous,  # handle incoming continuous data
                "STATE": self.l_state,  # The Pi is confirming/notifying us that it has changed state
                "HANDSHAKE": self.l_handshake,  # initial connection with some initial info
                "FILE": self.l_file,  # The pi needs some file from us
                "SESSION_FILES": self.l_session_files,  # The pi needs some file from us
            },
        )

        # dictionary that keep tracks of rigs
        self.rigs = rigs

        # start a timer at the draw FPS of the controller -- only send
        self.data_fps = 30
        self.data_ifps = 1.0 / self.data_fps

        self.loop = None

    def start_plot_timer(self):
        """
        Start a timer that controls video frame streaming frequency to GUI
        """
        self.plot_timer = threading.Thread(target=self._fps_clock)
        self.plot_timer.setDaemon(True)
        self.plot_timer.start()

    def _fps_clock(self):
        while not self.closing.is_set():
            for k, v in self.sent_plot.items():
                try:
                    v.set()
                except:
                    pass

            time.sleep(self.data_ifps)

    ####################
    # Message Handing Methods

    def l_ping(self, msg: Message):
        """
        Requested ping to confirm alive state.

        Respond with blank 'STATE' message.

        Args:
            msg

        """
        # respond with blank sice controller doesn't have states
        self.send(msg.sender, "STATE", flags={"NOLOG": True})

    def l_init(self, msg: Message):
        """
        Ask all rigs to confirm that they are alive

        Sends a "PING" to everyone in the rigs dictionary.

        Args:
            msg

        """
        # Ping all pis that we are expecting given our rig db
        # Responses will be handled with l_state so not much needed here

        for p in self.rigs.keys():
            self.send(p, "PING", flags={"NOLOG": True})

    def l_change(self, msg: Message):
        """
        Received change of parameter from the Pi

        Warning:
            Not Implemented
        Args:
            msg:

        """
        # Send through to controller
        self.send(to="_T", msg=msg)

        # # Send to plot widget, which should be listening to "P_{rig_name}"
        # # self.send('P_{}'.format(msg.value['rig']), 'DATA', msg.value, flags=msg.flags)
        # self.send(to="P_{}".format(msg.value["rig"]), msg=msg)

    def l_stopall(self, msg: Message):
        """
        Stop all rigs and plots
        Args:
            msg:
        """
        # let all the rigs and plot objects know that they should stop
        for p in self.rigs.keys():
            self.send(p, "STOP")
            self.send(f"P_{p}", "STOP")

    def l_data(self, msg: Message):
        """
        Stash incoming data from a rig

        Just forward this along to the internal controller object ('_T')
        and a copy to the relevant plot.

        Args:
            msg:

        """
        # Send through to controller
        # self.send('_T', 'DATA', msg.value, flags=msg.flags)
        self.send(to="_T", msg=msg)

        # Send to plot widget, which should be listening to "P_{rig_name}"
        # self.send('P_{}'.format(msg.value['rig']), 'DATA', msg.value, flags=msg.flags)
        self.send(to="P_{}".format(msg.value["rig"]), msg=msg)

    def l_continuous(self, msg: Message):
        """
        Handle the storage of continuous data
        Forwards all data on to the Controller's internal :class:`Net_Node`,
        send to :class:`.Plot` according to update rate in ``prefs.get('DRAWFPS')``
        Args:
            msg: A continuous data message
        """
        # Send through to controller
        # msg.value.update({'continuous':True})
        self.send(to="_T", msg=msg)

        # Send to plot widget, which should be listening to "P_{rig_name}"
        plot_id = "P_{}".format(msg.value["rig"])
        if plot_id in self.senders.keys():
            # if timer has not started
            if not self.plot_timer:
                self.start_plot_timer()

            # if don't have to wait, set the event immediately
            if msg.sender not in self.sent_plot.keys():
                self.sent_plot[msg.sender] = threading.Event()
            # when event is set, send the message to plot_id and clear event
            if self.sent_plot[msg.sender].is_set():
                self.send(to=plot_id, msg=msg)
                self.sent_plot[msg.sender].clear()

    def l_state(self, msg: Message):
        """
        A rig has changed state.

        Stash in 'state' field of rig dict and send along to _T

        Args:
            msg:

        """
        if msg.sender not in self.rigs.keys():
            self.rigs[msg.sender] = {}
            # if 'state' in self.rigs[msg.sender].keys():
            # if msg.value == self.rigs[msg.sender]['state']:
            #     # if we've already gotten this one, don't send to controller
            #     return

        self.rigs[msg.sender]["state"] = msg.value

        # Tell the controller so it can update the rig_db file
        state = {"state": msg.value, "rig": msg.sender}
        self.send("_T", "STATE", state)

        # Tell the plot
        self.send(f"P_{msg.sender}", "STATE", msg.value)

        self.senders[msg.sender] = msg.value

    def l_handshake(self, msg: Message):
        """
        A Pi is telling us it's alive and its IP.
        Send along to _T
        Args:
            msg:
        """
        # only rly useful for our controller object
        self.send("_T", "HANDSHAKE", value=msg.value)

    def l_file(self, msg: Message):
        """
        A rig needs some file from us.
        Send it back after :meth:`base64.b64encode` ing it.

        Todo:
            Split large files into multiple messages...

        Args:
            msg (:class:`.Message`): The value field of the message should contain some
                relative path to a file contained within `prefs.get('SOUNDDIR')` . eg.
                `'/songs/sadone.wav'` would return `'os.path.join(prefs.get('SOUNDDIR')/songs.sadone.wav'`

        """
        # The <target> pi has requested some file <value> from us, let's send it back
        # This assumes the file is small, if this starts crashing we'll have to split the message...

        full_path = os.path.join(prefs.get("STORE_DIRECTORY"), msg.value)
        with open(full_path, "rb") as open_file:
            # encode in base64 so json doesn't complain
            file_contents = base64.b64encode(open_file.read())

        file_message = {"path": msg.value, "file": file_contents}

        self.send(msg.sender, "FILE", file_message)

    def l_session_files(self, msg: Message):
        """
        Rig sent end of session files to be saved
        """
        # only rly useful for our controller object
        self.send("_T", "SESSION_FILES", value=msg.value)


class RigStation(Station):
    """
    :class:`~.networking.Station` object used by :class:`~.rig`
    objects.
    Spawned with a :attr:`~.Station.pusher` connected back to the
    :class:`~.Controller` .
    **Listens**
    +-------------+-------------------------------------+-----------------------------------------------+
    | Key         | Method                              | Description                                   |
    +=============+=====================================+===============================================+
    | 'STATE'     | :meth:`~.RigStation.l_state`     | rig has changed state                       |
    | 'COHERE'    | :meth:`~.RigStation.l_cohere`    | Make sure our data and the Controller's match.  |
    | 'PING'      | :meth:`~.RigStation.l_ping`      | The Controller wants to know if we're listening |
    | 'START'     | :meth:`~.RigStation.l_start`     | We are being sent a task to start             |
    | 'STOP'      | :meth:`~.RigStation.l_stop`      | We are being told to stop the current task    |
    | 'PARAM'     | :meth:`~.RigStation.l_change`    | The Controller is changing some task parameter  |
    | 'FILE'      | :meth:`~.RigStation.l_file`      | We are receiving a file                       |
    +-------------+-------------------------------------+-----------------------------------------------+
    """

    def __init__(self):
        # rig has a pusher - connects back to controller
        super(RigStation, self).__init__()
        self.pusher = True

        if prefs.get("LINEAGE") == "CHILD":
            self.push_id = prefs.get("PARENTID").encode("utf-8")
            self.push_port = prefs.get("PARENTPORT")
            self.push_ip = prefs.get("PARENTIP")
            self.child = True
        else:
            self.push_id = b"T"
            self.push_port = prefs.get("PUSHPORT")
            self.push_ip = prefs.get("CONTROLLERIP")
            self.child = False

        # Store some prefs values
        self.listen_port = prefs.get("MSGPORT")

        self.id = prefs.get("NAME")
        if self.id is None or self.id == "":
            # self.logger.exception(
            #     f"rig NAME in prefs.json cannot be blank, got {self.id}"
            # )
            raise ValueError(f"rig NAME in prefs.json cannot be blank, got {self.id}")
        self.pi_id = f"_{self.id}"
        self.subject = None  # Store current subject ID
        self.state = "IDLE"  # store current pi state
        self.child = False  # Are we acting as a child right now?
        self.parent = False  # Are we acting as a parent right now?

        self.listens.update(
            {
                "STATE": self.l_state,  # Confirm or notify controller of state change
                "COHERE": self.l_cohere,  # Sending our temporary data table at the end of a run to compare w/ controller's copy
                "PING": self.l_ping,  # The Controller wants to know if we're listening
                "START": self.l_start,  # We are being sent a task to start
                "STOP": self.l_stop,  # We are being told to stop the current task
                "PARAM": self.l_change,  # The Controller is changing some task parameter
                "EVENT": self.l_event,  # The Controller is sending some task event from GUI
                "FILE": self.l_file,  # We are receiving a file
                "CONTINUOUS": self.l_continuous,  # we are sending continuous data to the controller
                "CHILD": self.l_child,
                "HANDSHAKE": self.l_handshake,
                "CALIBRATE_PORT": self.l_forward,
                "CALIBRATE_RESULT": self.l_forward,
                "BANDWIDTH": self.l_forward,
                "STREAM_VIDEO": self.l_forward,
            },
        )

        # ping back our status to the controller every so often
        if prefs.get("PING_INTERVAL") is None:
            self.ping_interval = 5
        else:
            self.ping_interval = float(prefs.get("PING_INTERVAL"))

        self._ping_thread = threading.Timer(self.ping_interval, self._pinger)
        self._ping_thread.setDaemon(True)
        self._ping_thread.start()

    def _pinger(self):
        """
        Periodically ping the controller with our status

        Calls its own timer to replace it

        Returns:

        """
        # before .run is called, pusher is a boolean flag telling us to make one when it is
        # not great and should be changed, but these modules are not long for this world
        # in their current form anyway
        if not isinstance(self.pusher, bool):
            self.l_ping()
        if not self.closing.is_set():
            self._ping_thread = threading.Timer(self.ping_interval, self._pinger)
            self._ping_thread.setDaemon(True)
            self._ping_thread.start()

    ###########################
    # Message/Listen handling methods

    def l_noop(self, msg):
        pass

    def l_state(self, msg: Message):
        """
        Rig has changed state

        Stash it and alert the Controller

        Args:
            msg (:class:`.Message`):

        """
        # Save locally so we can respond to queries on our own, then push 'er on through
        # Value will just have the state, we want to add our name
        self.state = msg.value

        self.push(to=self.push_id, key="STATE", value=msg.value)

    def l_cohere(self, msg: Message):
        """
        Send our local version of the data table so the controller can double check
        Warning:
            Not Implemented
        Args:
            msg (:class:`.Message`):
        """

    def l_ping(self, msg: Message = None):
        """
        The Controller wants to know our status
        Push back our current state.

        Args:
            msg (:class:`.Message`):

        """
        # The controller wants to know if we are alive, respond with our name and IP
        # don't bother the pi
        self.push(key="STATE", value=self.state, flags={"NOLOG": True})

    def l_change(self, msg: Message):
        """
        The controller is changing a parameter
        Warning:
            Not implemented
        Args:
            msg (:class:`.Message`):
        """
        # TODO: Changing some task parameter from the Controller
        self.send(self.pi_id, "PARAM", msg.value)

    def l_start(self, msg: Message):
        """
        We are being sent a task to start
        If we need any files, request them.
        Then send along to the rig.

        Args:
            msg (:class:`.Message`): value will contain a dictionary containing a task
                description.

        """
        self.send(self.pi_id, "START", msg.value)

    def l_stop(self, msg: Message):
        """
        Tell the pi to stop the task
        Args:
            msg (:class:`.Message`):
        """
        self.send(self.pi_id, "STOP")

    def l_event(self, msg: Message):
        """
        Forward the event to rig
        Args:
            msg (:class:`.Message`):
        """
        self.send(self.pi_id, "EVENT", msg.value)

    def l_file(self, msg: Message):
        """
        We are receiving a file.
        Decode from b64 and save. Set the file_block.

        Args:
            msg (:class:`.Message`): value will have 'path' and 'file',
                where the path determines where in `prefs.get('SOUNDDIR')` the
                b64 encoded 'file' will be saved.

        """
        # The file should be of the structure {'path':path, 'file':contents}
        full_path = os.path.join(prefs.get("SOUNDDIR"), msg.value["path"])
        # TODO: give Message full deserialization capabilities including this one
        file_data = base64.b64decode(msg.value["file"])
        try:
            os.makedirs(os.path.dirname(full_path))
        except:
            # TODO: Make more specific - only if dir already exists
            pass
        with open(full_path, "wb") as open_file:
            open_file.write(file_data)

        self.logger.info("SOUND RECEIVED {}".format(msg.value["path"]))        # If we requested a file, some poor start fn is probably waiting on us
        self.file_block.set()

    def l_handshake(self, msg: Message):
        """
        Forward handshake message from rig to controller.
        
        Args:
            msg (:class:`Message`): Handshake message from rig
        """
        # Forward the handshake message to the controller
        self.push(to="T", key="HANDSHAKE", value=msg.value)
        self.logger.debug(f"Forwarding handshake from {msg.sender} to controller")

    def l_continuous(self, msg: Message):
        """
        Forwards continuous data sent by children back to controller.
        Continuous data sources from this rig should be streamed directly to the controller.

        Args:
            msg (:class:`Message`): Continuous data message

        """
        if self.child:
            msg.value["rig"] = self.parent_id
            msg.value["subject"] = self.subject
            msg.value["continuous"] = True
            self.push(to="T", key="DATA", value=msg.value, repeat=False)
        else:
            self.logger.warning(
                "Received continuous data but no child found, \
                                continuous data should be streamed directly to controller \
                                from rig",
            )

    def l_child(self, msg: Message):
        """
        Tell one or more children to start running a task.
        By default, the `key` argument passed to `self.send` is 'START'.
        However, this can be overriden by providing the desired string
        as `msg.value['KEY']`.
        This checks the pref `CHILDID` to get the names of one or more children.
        If that pref is a string, sends the message to just that child.
        If that pref is a list, sends the message to each child in the list.

        Args:
            msg (): A message to send to the child or children.

        Returns:
            nothing

        """
        # Take `KEY` from msg.value['KEY'] if available
        # Otherwise, use 'START'
        if "KEY" in msg.value.keys():
            KEY = msg.value["KEY"]
        else:
            KEY = "START"

        # Get the list of children
        pref_childid = prefs.get("CHILDID")

        # Send to one or more children
        if isinstance(pref_childid, list):
            # It's a list of multiple children, send to each
            for childid in pref_childid:
                self.send(to=childid, key=KEY, value=msg.value)
        else:
            # Send to the only child
            self.send(to=pref_childid, key=KEY, value=msg.value)

    def l_forward(self, msg: Message):
        """
        Just forward the message to the pi.
        """
        self.send(to=self.pi_id, key=msg.key, value=msg.value)


if __name__ == "main":
    a = RigStation()
    print(2)
