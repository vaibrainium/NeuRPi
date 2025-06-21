import time
import multiprocessing as mp
import zmq


def sender_ipc(queue, num_messages):
    context = zmq.Context()
    sender_socket = context.socket(zmq.PUSH)
    sender_socket.bind("ipc:///tmp/sender_endpoint")

    for i in range(num_messages):
        start_time = time.time()
        message = b"Hello, World!"  # Sample message
        sender_socket.send(message)
        queue.put(start_time)

    sender_socket.close()


def receiver_ipc(queue, num_messages):
    context = zmq.Context()
    receiver_socket = context.socket(zmq.PULL)
    receiver_socket.connect("ipc:///tmp/sender_endpoint")

    total_latency = 0
    for i in range(num_messages):
        receiver_socket.recv()
        end_time = time.time()
        start_time = queue.get()
        latency = (end_time - start_time) * 1000  # in milliseconds
        total_latency += latency

    receiver_socket.close()
    average_latency = total_latency / num_messages
    queue.put(average_latency)


def sender_tcp(queue, num_messages):
    context = zmq.Context()
    sender_socket = context.socket(zmq.PUSH)
    sender_socket.bind("tcp://127.0.0.1:5555")

    for i in range(num_messages):
        start_time = time.time()
        message = b"Hello, World!"  # Sample message
        sender_socket.send(message)
        queue.put(start_time)

    sender_socket.close()


def receiver_tcp(queue, num_messages):
    context = zmq.Context()
    receiver_socket = context.socket(zmq.PULL)
    receiver_socket.connect("tcp://127.0.0.1:5555")

    total_latency = 0
    for i in range(num_messages):
        receiver_socket.recv()
        end_time = time.time()
        start_time = queue.get()
        latency = (end_time - start_time) * 1000  # in milliseconds
        total_latency += latency

    receiver_socket.close()
    average_latency = total_latency / num_messages
    queue.put(average_latency)


def sender_mp(queue, num_messages):
    for i in range(num_messages):
        start_time = time.time()
        message = "Hello, World!"  # Sample message
        queue.put((message, start_time))


def receiver_mp(queue, num_messages):
    total_latency = 0
    for i in range(num_messages):
        message, start_time = queue.get()
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # in milliseconds
        total_latency += latency

    average_latency = total_latency / num_messages
    queue.put(average_latency)


def main():
    num_messages = 1000
    ipc_queue = mp.Queue()
    tcp_queue = mp.Queue()
    mp_queue = mp.Queue()

    # IPC
    ipc_sender_process = mp.Process(target=sender_ipc, args=(ipc_queue, num_messages))
    ipc_receiver_process = mp.Process(target=receiver_ipc, args=(ipc_queue, num_messages))

    # TCP
    tcp_sender_process = mp.Process(target=sender_tcp, args=(tcp_queue, num_messages))
    tcp_receiver_process = mp.Process(target=receiver_tcp, args=(tcp_queue, num_messages))

    # Multiprocessing Queue
    mp_sender_process = mp.Process(target=sender_mp, args=(mp_queue, num_messages))
    mp_receiver_process = mp.Process(target=receiver_mp, args=(mp_queue, num_messages))

    processes = [
        ipc_sender_process,
        ipc_receiver_process,
        tcp_sender_process,
        tcp_receiver_process,
        mp_sender_process,
        mp_receiver_process,
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    ipc_average_latency = ipc_queue.get()
    tcp_average_latency = tcp_queue.get()
    mp_average_latency = mp_queue.get()

    # print(f"IPC Average Latency: {ipc_average_latency:.2f} ms")
    # print(f"TCP Average Latency: {tcp_average_latency:.2f} ms")
    # print(f"Multiprocessing Queue Average Latency: {mp_average_latency:.2f} ms")

    return ipc_average_latency, tcp_average_latency, mp_average_latency


if __name__ == "__main__":
    ipc_time, tcp_time, mp_time = main()
    print(f"IPC Average Latency: {ipc_time:.2f} ms")
    print(f"TCP Average Latency: {tcp_time:.2f} ms")
    print(f"Multiprocessing Queue Average Latency: {mp_time:.2f} ms")

    # total_ipc_time = 0
    # total_tcp_time = 0
    # total_mp_time = 0
    # for i in range(100):
    #     print(i)
    #     ipc_time, tcp_time, mp_time = main()
    #     total_ipc_time += ipc_time
    #     total_tcp_time += tcp_time
    #     total_mp_time += mp_time

    # print(f"IPC Average Latency: {total_ipc_time/100:.2f} ms")
    # print(f"TCP Average Latency: {total_tcp_time/100:.2f} ms")
    # print(f"Multiprocessing Queue Average Latency: {total_mp_time/100:.2f} ms")
