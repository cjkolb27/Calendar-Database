import socket
import threading

def handleClient(connId, end):
    
    clientHost = ""
    clientPort = ""

    while(end[0]):
        try:
            data = connId.recv(1024)
        except Exception as e:
            print(f"Client {clientHost} has left the server.\n")
            return

        if not end[0]:
            return
        
        if not data:
            print(f"Client {clientHost} has left the server.\n")
            return
        
        data = data.decode()
        print("\r\n" + data)
        parse = data.split("\r\n")
        try:
            line1 = parse[0].split(" ")
            if len(line1) == 2 and line1[0] == "Post":
                if line1[1] != version():
                    print(f"Client {clientHost} has left the server.\n")
                    return
                line2 = parse[1].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    return
                clientHost = line2[1]
                print(f"Client: {clientHost} has conencted.")

            
        except:
            return
        


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
    serverThreads = []
    connections = []
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

        thread = threading.Thread(target=handleClient, args=(connId, end,))
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

