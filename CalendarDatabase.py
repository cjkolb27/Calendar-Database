import socket
import threading

def handleClientRecieving(connId, end):
    
    clientHost = ""
    clientPort = ""
    client = None
    firstTime = True

    while(end[0]):
        try:
            data = connId.recv(1024)
        except Exception as e:
            print(f"Client {clientHost} has left the server.\n")
            if client != None:
                client.close
                clients.remove(client)
            break

        if not end[0]:
            break
        
        if not data:
            print(f"Client {clientHost} has left the server.\n")
            break
        
        data = data.decode()
        print("\r\n" + data)
        parse = data.split("\r\n")
        try:
            line1 = parse[0].split(" ")
            if len(line1) != 2 and line1[1] != version():
                print(f"Client {clientHost} has left the server.\n")
                break
            if line1[0] == "Post" and firstTime:
                firstTime = False
                line2 = parse[1].split(" ")
                line3 = parse[2].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    break
                clientHost = line2[1]
                clientPort = line3[1]
                print(f"Client: {clientHost} has conencted.")
                with clients_lock:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((socket.gethostbyname(clientHost), int(clientPort)))
                    clients.append(client)
                broadcast() 
            
            if line1[0] == "Put":
                line2 = parse[1].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    break
        except:
            break
    return

def broadcast():
    with clients_lock:
        for client in clients:
            client.sendall("Hello this is a test broadcast\r\n\r\n".encode())
    return

def serverInputHandler(end):
    cmd = input("")
    while(cmd != "Quit"):
        cmd = input("")
    end[0] = False
    serverSocket.close()

def version():
    return "Ver1.0"

if __name__ == "__main__":
    end = [True]
    clients_lock = threading.Lock()
    serverThreads = []
    connections = []
    clients = []
    serverHostname = socket.gethostname()
    serverPort = 2727
    processCount = 1

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    serverSocket.bind((serverHostname, serverPort))
    print(f"Server is connected port {serverPort}, Hostname: {serverHostname}")

    serverSocket.listen()

    thread = threading.Thread(target=serverInputHandler, args=(end,))
    serverThreads.append(thread)
    thread.start()

    while(end[0]):
        try:
            connId, addrInfo = serverSocket.accept()
            connections.append(connId)
        except OSError:
            break

        if not end:
            break

        thread = threading.Thread(target=handleClientRecieving, args=(connId, end,))
        serverThreads.append(thread)
        processCount += 1
        thread.start()

    # Close all connections
    for id in connections:
        id.close()
    print("\nClosed Server.")

    # Join all threads
    for serverThread in serverThreads:
        serverThread.join()
    print("Threads Closed")

