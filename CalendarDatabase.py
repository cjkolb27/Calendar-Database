import socket
import threading
import os
import datetime
from pathlib import Path

def handleClientRecieving(connId, end):
    
    clientHost = ""
    clientPort = ""
    client = None
    firstTime = True
    data = ""

    while(end[0]):
        try:
            if len(data) == 0:
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
        
        foundData = data[:(data.find("\r\n\r\n") + 4)]
        data = data[(data.find("\r\n\r\n") + 4):]
        while data.find("\r\n") == 0:
            data = data[2:]

        print("Data:\r\n" + foundData)
        parse = foundData.split("\r\n")
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
                line6 = parse[5:]
                print(line6)
                line6 = line6[:-2]
                print(line6)
                version = parse[3].split(" ")[1]
                if len(line2) != 2 or line2[0] != "Host:":
                    print(f"Client {clientHost} has left the server.\n")
                    break

                with clients_lock:
                    updateCalendar(client, version, parse[4], line6)
                    print("Finished!!!!")
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
    print(f"{client} {version} {file} {changes}")
    changed = []
    fileData = ""
    with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "r") as theFile:
        split = changes[0].split("@@")
        theVersion = int(theFile.readline()) + 1
        serverVersion = theVersion
        fileData = f"{theVersion}\r\n"
        fileLine = theFile.readline()
        deleted = None
        found = False
        while fileLine:
            found = False
            if len(changes) > 0:
                line = fileLine.split("@@")
                if split[0] == "NotSynced":
                    if (int(line[3]) > int(split[5]) and int(line[4]) == int(split[6])) or (int(line[4]) > int(split[6])) or (int(line[3]) == int(split[5]) and int(line[4]) == int(split[6]) and time_to_int(line[1]) > time_to_int(split[3])):
                        fileData += "@@".join(split[2:]) + "\r\n"
                        found = True
                        print(f"{(int(line[3]) > int(split[5]) and int(line[4]) == int(split[6]))} or {(int(line[4]) > int(split[6]))} or {(int(line[3]) == int(split[5]) and int(line[4]) == int(split[6]) and time_to_int(line[1]) > time_to_int(split[3]))}")
                        changed.append(changes[0])
                        changes = changes[1:]
                        if len(changes) > 0:
                            split = changes[0].split("@@")
                        else:
                            split[0] = "NULL"
                    else:
                        fileData += fileLine
                elif split[0] == "Deleted":
                    if deleted == None:
                        deleted = split[1].split("/")
                    print(f"Diff {line[9]} {deleted[11]}")
                    if line[9] == deleted[11] and line[1] == deleted[3] and line[3] == deleted[5] and line[4] == deleted[6]:
                        print(f"FOUND: {line[9]} {deleted[11]}")
                        changed.append(changes[0])
                        changes = changes[1:]
                        if len(changes) > 0:
                            split = changes[0].split("@@")
                        else:
                            split[0] = "NULL"
                        deleted = None
                    else:
                       fileData += fileLine 
                elif split[0] == "Edited":
                    if deleted == None:
                        deleted = split[1].split("/")
                    print(f"Diff {line[9]} {deleted[11]}")
                    if line[9] == deleted[11] and line[1] == deleted[3] and line[3] == deleted[5] and line[4] == deleted[6]:
                        print(f"FOUND: {line[9]} {deleted[11]} {"@@".join(split[1].split("/")[2:])}")
                        fileData += "@@".join(split[2:]) + "\r\n"
                        changed.append(changes[0])
                        changes = changes[1:]
                        if len(changes) > 0:
                            split = changes[0].split("@@")
                        else:
                            split[0] = "NULL"
                        deleted = None
                    else:
                       fileData += fileLine 
                else:
                    fileData += fileLine
            else:
                fileData += fileLine
            if not found:
                fileLine = theFile.readline()
        while len(changes) > 0:
            print("TEST2")
            if changes[0] == "":
                break
            if split[0] == "NotSynced":
                fileData += "@@".join(split[2:]) + "\r\n"
                changed.append(changes[0])
                changes = changes[1:]
                if len(changes) > 0:
                    split = changes[0].split("@@")
            if split[0] == "Edited" or split[0] == "Deleted":
                changes = changes[1:]
                if len(changes) > 0:
                    split = changes[0].split("@@")
        #print(fileData)
    with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "w", newline='') as newFile:
        newFile.write(fileData)

    if len(changed) > 0:
        print(f"Changed: {changed}")
        broadcast(f"Put\r\nFile: {file}\r\nVersion: {serverVersion}\r\n{"\r\n".join(changed)}")
    return

def broadcast(message):
    print(f"\r\nBroadcasted: {message}\r\n")
    for client in clients:
        try:
            client.sendall(f"{message}\r\n\r\n".encode())
        except Exception as e:
            clients.remove(client)
            print(e)
    return

def time_to_int(t): 
    time = 0
    t = t.replace(":", "")
    if "a" in t:
        t = t.replace("a", "")
        time = int(t)
        if time >= 1200:
            time -= 1200
    else:
        t = t.replace("p", "")
        time = int(t)
        if time < 1200:
            time += 1200
    return time

def serverInputHandler(end):
    cmd = input("")
    while(cmd != "q" and cmd != "quit"):
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
    serverVersion = "Ver1.0"

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

