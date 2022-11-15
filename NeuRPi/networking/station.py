import base64
import multiprocessing
import os
import socket
import threading
import time
import typing
from copy import copy
from itertools import count
from typing import Optional, Union

import zmq
from tornado.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking.message import Message


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
        super(Network, self).__init__()
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
            Warning("Couldn't get IP: {}".format(e))
            self.ip = ""

        self.file_block = multiprocessing.Event()  # to wait for file transfer

        # Count and number messages as we send them
        self.msg_counter = count()

        # Few built-in listens
        if listens is None:
            listens = {}
        self.listens = listens
        self.listens.update(
            {"CONFIRM": self.l_confirm, "STREAM": self.l_stream, "KILL": self.l_kill}
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
        Find our IP address
        returns (str): our IPv4 address.
        """
        # shamelessly stolen from https://www.w3resource.com/python-exercises/python-basic-exercise-55.php
        # variables are badly named because this is just a rough unwrapping of what was a monstrous one-liner
        # (and i don't really understand how it works)

        # get ips that aren't the loopback
        unwrap00 = [
            ip
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]
            if not ip.startswith("127.")
        ][:1]
        # ??? truly dk
        unwrap01 = [
            [
                (s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close())
                for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
            ][0][1]
        ]
        unwrap2 = [l for l in (unwrap00, unwrap01) if l][0][0]
        return unwrap2

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
        msg.id = "{}_{}".format(self.id, msg_num)

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
                "Need either a message or 'to' and 'key' fields.\
                Got\nto: {}\nkey: {}\nvalue: {}\nmsg: {}".format(
                    to, key, value, msg
                )
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
            self.logger.exception("Message Invalid:\n{}".format(str(msg)))

        # Encode message
        msg_enc = msg.serialize()

        if not msg_enc:
            self.logger.exception("Message could not be encoded:\n{}".format(str(msg)))
            return

        if manual_to:
            self.listener.send_multipart([to.encode("utf-8"), msg_enc])
        else:

            if isinstance(msg.to, list):

                self.listener.send_multipart(
                    [*[hop.encode("utf-8") for hop in to], msg_enc]
                )
            else:
                self.listener.send_multipart([msg.to.encode("utf-8"), msg_enc])

        self.logger.debug("MESSAGE SENT - {}".format(str(msg)))

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
                "Need either a message or 'to' and 'key' fields.\
                Got\nto: {}\nkey: {}\nvalue: {}\nmsg: {}".format(
                    to, key, value, msg
                )
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
            self.logger.exception("Message Invalid:\n{}".format(str(msg)))

        # Encode message
        msg_enc = msg.serialize()

        if not msg_enc:
            self.logger.exception("Message could not be encoded:\n{}".format(str(msg)))
            return

        # Even if the message is not to our upstream node, we still send it
        # upstream because presumably our target is upstream.
        self.pusher.send_multipart(
            [self.push_id, bytes(msg.to, encoding="utf-8"), msg_enc]
        )

        if not (msg.key == "CONFIRM") and log_this:
            self.logger.debug("MESSAGE PUSHED - {}".format(str(msg)))

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
        if msg.to == "_{}".format(self.id):
            self.send("_{}".format(self.id), "CONFIRM", msg.value)

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
        Terminal wants us to die :(
        Stop the :attr:`.Station.loop`
        Args:
            msg (:class:`.Message`):
        """
        self.logger.info("Received kill request")

        self.closing.set()

        # Stopping the loop should kill the process, as it's what's holding us in run()
        self.listener.stop_on_recv()
        self.listener.close()

        if self.pusher:
            self.listener.stop_on_recv()
            self.pusher.close()

        self.loop.add_callback(lambda: IOLoop.instance().stop())
        self.logger.debug(self.loop)
        self.logger.info("Stopped IOLoop")

    def release(self):
        self.closing.set()

        # sending a message to ourselves from the parent process to this one
        ctx = zmq.Context().instance()
        sock = ctx.socket(zmq.DEALER)
        sock.setsockopt_string(zmq.IDENTITY, f"{self.id}/closer")
        sock.connect(f"tcp://localhost:{self.listen_port}")
        sock.send_multipart([self.id.encode("utf-8", "CLOSING".encode("utf-8"))])
        sock.close()
        # Terminate mulitiprocess.Process()
        self.terminate()

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
                            "PUBLISH FAILED {} - {}".format(id, str(push_outbox[id][1]))
                        )
                        try:
                            del self.push_outbox[id]
                        except KeyError:
                            # fine, already deleted
                            pass
                    else:
                        # if we didn't just put this message in our outbox
                        if (
                            time.time() - push_outbox[id][0]
                        ) > self.repeat_interval * 2:

                            self.logger.debug(
                                "REPUBLISH {} - {}".format(id, str(push_outbox[id][1]))
                            )
                            self.pusher.send_multipart(
                                [self.push_id, push_outbox[id][1].serialize()]
                            )
                            self.push_outbox[id][1].ttl -= 1

            if len(send_outbox) > 0:
                for id in send_outbox.keys():
                    if send_outbox[id][1].ttl <= 0:
                        self.logger.warning(
                            "PUBLISH FAILED {} - {}".format(id, str(send_outbox[id][1]))
                        )
                        try:
                            del self.send_outbox[id]
                        except KeyError:
                            # fine, already deleted
                            pass

                    else:
                        # if we didn't just put this message in our outbox
                        if (
                            time.time() - send_outbox[id][0]
                        ) > self.repeat_interval * 2:

                            self.logger.debug(
                                "REPUBLISH {} - {}".format(id, str(send_outbox[id][1]))
                            )
                            self.listener.send_multipart(
                                [
                                    bytes(send_outbox[id][1].to, encoding="utf-8"),
                                    send_outbox[id][1].serialize(),
                                ]
                            )
                            self.send_outbox[id][1].ttl -= 1

            # wait to do it again
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
            self.listener.bind("tcp://*:{}".format(self.listen_port))
            self.listener = ZMQStream(self.listener, self.loop)
            self.listener.on_recv(self.handle_listen)

            if self.pusher is True:
                self.pusher = self.context.socket(zmq.DEALER)
                self.pusher.setsockopt_string(zmq.IDENTITY, self.id)
                self.pusher.connect("tcp://{}:{}".format(self.push_ip, self.push_port))
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
            pass
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
            if unserialized_to.decode("utf-8") not in [self.id, "_{}".format(self.id)]:
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
                else:
                    if unserialized_to not in self.senders.keys() and self.pusher:
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
            self.logger.error("Dont know what this message is:{}".format(msg))
            return

        ###################################
        # Handle the message

        # unstack and listed to fields remaining from forwarding
        if isinstance(msg.to, list):
            if len(msg.to) == 1:
                msg.to = msg.to[0]

        # if this message is to us, just handle it and return
        if msg.to in [self.id, "_{}".format(self.id)]:
            if msg.key != "CONFIRM":
                self.logger.debug("RECEIVED: {}".format(str(msg)))
            # Log and spawn thread to respond to listen
            try:
                listen_funk = self.listens[msg.key]
                listen_thread = threading.Thread(target=listen_funk, args=(msg,))
                listen_thread.start()
            except KeyError:
                self.logger.exception(
                    "No function could be found for msg id {} with key: {}".format(
                        msg.id, msg.key
                    )
                )

            # send a return message that confirms even if we except
            # don't confirm confirmations
            if (msg.key != "CONFIRM") and ("NOREPEAT" not in msg.flags.keys()):
                if send_type == "router":
                    self.send(msg.sender, "CONFIRM", msg.id)
                elif send_type == "dealer":
                    self.push(msg.sender, "CONFIRM", msg.id)
            return
        elif self.child and (msg.to == "T"):
            # FIXME UGLY HACK
            self.push(msg=msg)
        else:
            self.logger.exception(
                f"Message not to us, but wasnt forwarded previously in handling method, message must be misformatted: {msg}"
            )
