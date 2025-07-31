import socket
import threading
import os
from pathlib import Path

def handleClientRecieving(connId, end):
    
    clientHost = ""
    clientPort = ""
    client = None
    firstTime = True
    data = ""

    while(end[0]):
        try:
            data = connId.recv(1024).decode()
            if not data:
                print(f"Client {clientHost} has left the server.\n")
                if client != None:
                    with clients_lock:
                        client.close
                        clients.remove(client)
                break
            while "\r\n\r\n" not in data:
                sent = connId.recv(1024).decode()
                if not sent or not data:
                    if client != None:
                        with clients_lock:
                            client.close
                            clients.remove(client)
                    return
                data += sent

        except Exception as e:
            print(f"{e}\r\nClient {clientHost} has left the server.\n")
            if client != None:
                with clients_lock:
                    client.close
                    clients.remove(client)
            break

        if not end[0]:
            break
        
        print("\r\n" + data)
        parse = data.split("\r\n")
        try:
            line1 = parse[0].split(" ")
            if len(line1) != 2 and line1[1] != version():
                print(f"Client {clientHost} has left the server.\n")
                if client != None:
                    with clients_lock:
                        client.close
                        clients.remove(client)
                break
            if line1[0] == "Get" and firstTime:
                firstTime = False
                line2 = parse[1].split(" ")
                line3 = parse[2].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    if client != None:
                        with clients_lock:
                            client.close
                            clients.remove(client)
                    break
                clientHost = line2[1]
                clientPort = line3[1]
                print(f"Client: {clientHost} has conencted.")
                with clients_lock:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((socket.gethostbyname(clientHost), int(clientPort)))
                    clients.append(client)
                ## broadcast("Hello, another client has join the server.")
                file = parse[4]
                print(f"{file}")
                with clients_lock:
                    sendCalendar(client, file)

            if line1[0] == "Post":
                firstTime = False
                line2 = parse[1].split(" ")
                line3 = parse[2].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    if client != None:
                        with clients_lock:
                            client.close
                            clients.remove(client)
                    break
                with clients_lock:
                    file = parse[4]
                    version = parse[5]
                    events = parse[5:]
                    with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "w", newline='') as newFile:
                        for line in events[:-3]:
                            newFile.write(line + "\r\n")
                    print("File writen")

            
            if line1[0] == "Put":
                line2 = parse[1].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    break
                
                with clients_lock:
                    print()

            if line1[0] == "Puts":
                line2 = parse[1].split(" ")
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    break

        except:
            break
    return

def sendCalendar(client, file):
    try:
        os.mkdir("CalendarDatabase")
    except Exception:
        print()
    if not (Path(__file__).parent / "CalendarDatabase" / f"{file}").exists():
        try:
            client.sendall(f"Get\r\nFile: {file}\r\n\r\n".encode())
        except Exception as e:
            print(e) 
        return
    with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "r") as file:
        fileData = file.read()
        client.sendall(f"Post\r\n{fileData}\r\n\r\n".encode())
    return

def updateCalendar(client, version, file, changes):
    return

def broadcast(message):
    print(f"\r\nBroadcasted: {message}\r\n")
    for client in clients:
        try:
            client.sendall(f"{message}\r\n\r\n".encode())
        except Exception as e:
            print(e)
    return

def serverInputHandler(end):
    cmd = input("")
    while(cmd != "Quit"):
        broadcast(cmd)
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

