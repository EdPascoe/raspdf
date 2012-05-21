import socket
from multiprocessing import Process, Queue
import multiprocessing
import cPickle as pickle

QMAX=5
CHILDREN=5

q=Queue(QMAX)

def qhandle():
  while True:
    logger = logging.getLogger("Qhandle")
    msg = q.get()
    connection, address = pickle.loads(msg)
    handle(connection, address)


def handle(connection, address):
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("process-%r" % (address,))
    try:
        logger.debug("Connected %r at %r", connection, address)
        while True:
            data = connection.recv(1024)
            if data == "":
                logger.debug("Socket closed remotely")
                break
            logger.debug("Received data %r", data)
            connection.sendall(data)
            logger.debug("Sent data")
    except:
        logger.exception("Problem handling request")
    finally:
        logger.debug("Closing socket")
        connection.close()

class Server(object):
    def __init__(self, hostname, port):
        import logging
        self.logger = logging.getLogger("server")
        self.hostname = hostname
        self.port = port

    def start(self):
        self.logger.debug("listening")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.hostname, self.port))
        self.socket.listen(1)

        while True:
            conn, address = self.socket.accept()
            self.logger.debug("Got connection")
            q.put( pickle.dumps((conn, address)))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    for i in xrange(CHILDREN):
      process = Process(target=qhandle)
      process.daemon = True
      process.start()
      
    server = Server("0.0.0.0", 9001)
    try:
        logging.info("Listening")
        server.start()
    except:
        logging.exception("Unexpected exception")
    finally:
        logging.info("Shutting down")
        for process in multiprocessing.active_children():
            logging.info("Shutting down process %r", process)
            process.terminate()
            process.join()
    logging.info("All done")

