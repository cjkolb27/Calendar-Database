import socket
import threading
import os
from pathlib import Path
import mariadb
import sys
import os
from dotenv import load_dotenv
from datetime import timedelta

def handleClientRecieving(connId, end, db):
    
    clientHost = ""
    clientPort = ""
    client = None
    firstTime = True
    data = ""

    while not end[0]:
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

        if end[0]:
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
                    sendCalendar(client, file, db)

            if line1[0] == "Post":
                print("Trying to post")
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
                    file = parse[3][:4]
                    version = parse[4]
                    events = parse[5:]
                    print(f"{file}, {version}, {events}")
                    db.execute("UPDATE Versions SET version=? WHERE vyear=?", (int(version), int(file),))
                    print(f"Rows updated: {db.rowcount}")
                    for event in events:
                        print(event)
                        sp = event.split("@@")
                        if len(sp) > 2:
                            db.execute("INSERT INTO Events (name, startTime, endTime, day, month, year, red, green, blue, tstamp) Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (sp[0], convertTime(sp[1]), convertTime(sp[2]), int(sp[3]), int(sp[4]), int(sp[5]), int(sp[6]), int(sp[7]), int(sp[8]), sp[9],))
                            print(f"Inserted count: {db.rowcount}")
                    print("Database updated")

            
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
                    updateCalendar(client, version, parse[4], line6, db)
                    print("Finished!!!!")
        except:
            break
    return

def sendCalendar(client, file, db):
    try:
        db.execute("SELECT * FROM Versions WHERE vyear=?", (file.split(".")[0],))
        rows = db.fetchall()
        print(f"Rows: {rows}")
        if not rows:
            db.execute("INSERT INTO Versions (vyear, version) Values (?, ?)", (file.split(".")[0], 0,))
            client.sendall(f"Get\r\n{file}\r\n\r\n".encode())
            print("Getting from the client.")
            return
        else:
            y, v = rows[0]
            db.execute("SELECT * FROM Events WHERE year=?", (int(y),))
            rows = db.fetchall()
            print(f"Rows: {rows}")
            data = f"{v}\r\n"
            for row in rows:
                _, name, startTime, endTime, day, month, year, red, green, blue, timestamp = row
                data += f"{name}@@{revertTime(startTime)}@@{revertTime(endTime)}@@{day}@@{month}@@{year}@@{red}@@{green}@@{blue}@@{timestamp}@@\r\n"
            print(f"Post\r\n{data}\r\n")
            client.sendall(f"Post\r\n{data}\r\n".encode())
    except Exception as e:
        print(e)
        return
    return

def updateCalendar(client, version, file, changes, db):
    try:
        print(f"{client} {version} {file} {changes}")
        changed = []
        for change in changes:
            split = change.split("@@")
            if split[0] == "NotSynced":
                db.execute("INSERT INTO Events (name, startTime, endTime, day, month, year, red, green, blue, tstamp) Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (split[2], convertTime(split[3]), convertTime(split[4]), int(split[5]), int(split[6]), int(split[7]), int(split[8]), int(split[9]), int(split[10]), split[11],))
                _ = db.rowcount
                changed.append(change)
            elif split[0] == "Deleted":
                sp = split[1].split("/")
                db.execute("SELECT eid FROM Events WHERE day=? AND month=? AND year=? AND tstamp=?", (int(split[5]), int(split[6]), int(split[7]), sp[11],))
                count = db.rowcount
                if count == 1:
                    id = db.fetchall()[0][0]
                    db.execute("DELETE FROM Events WHERE eid=?", (int(id),))
                    if db.rowcount == 1:
                        changed.append(change)
            elif split[0] == "Edited":
                sp = split[1].split("/")
                db.execute("SELECT eid FROM Events WHERE day=? AND month=? AND year=? AND tstamp=?", (int(sp[5]), int(sp[6]), int(sp[7]), sp[11],))
                count = db.rowcount
                print(f"The count: {count}")
                if count == 1:
                    id = db.fetchall()[0][0]
                    print(f"The ID: {id}")
                    db.execute("UPDATE Events SET name=?, startTime=?, endTime=?, day=?, month=?, year=?, red=?, green=?, blue=?, tstamp=? WHERE eid=?", (split[2], convertTime(split[3]), convertTime(split[4]), int(split[5]), int(split[6]), int(split[7]), int(split[8]), int(split[9]), int(split[10]), split[11], int(id),))
                    if db.rowcount == 1:
                        changed.append(change)

        if len(changed) > 0:
            print(f"Changed: {changed}")
            db.execute("SELECT * FROM Versions WHERE vyear=?", (file.split(".")[0],))
            rows = db.fetchall()
            y, v = rows[0]
            db.execute("UPDATE Versions SET version=? WHERE vyear=?", (int(v) + 1, int(y),))
            _ = db.rowcount
            broadcast(f"Put\r\nFile: {file}\r\nVersion: {int(v) + 1}\r\n{"\r\n".join(changed)}")

    except Exception as e:
        print(e)

# def updateCalendar(client, version, file, changes):
#     print(f"{client} {version} {file} {changes}")
#     changed = []
#     fileData = ""
#     try:
#         with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "r") as theFile:
#             split = changes[0].split("@@")
#             theVersion = int(theFile.readline()) + 1
#             serverVersion = theVersion
#             fileData = f"{theVersion}\r\n"
#             fileLine = theFile.readline()
#             deleted = None
#             found = False
#             while fileLine:
#                 found = False
#                 if len(changes) > 0:
#                     line = fileLine.split("@@")
#                     if split[0] == "NotSynced":
#                         if (int(line[3]) > int(split[5]) and int(line[4]) == int(split[6])) or (int(line[4]) > int(split[6])) or (int(line[3]) == int(split[5]) and int(line[4]) == int(split[6]) and time_to_int(line[1]) > time_to_int(split[3])):
#                             fileData += "@@".join(split[2:]) + "\r\n"
#                             found = True
#                             print(f"{(int(line[3]) > int(split[5]) and int(line[4]) == int(split[6]))} or {(int(line[4]) > int(split[6]))} or {(int(line[3]) == int(split[5]) and int(line[4]) == int(split[6]) and time_to_int(line[1]) > time_to_int(split[3]))}")
#                             changed.append(changes[0])
#                             changes = changes[1:]
#                             if len(changes) > 0:
#                                 split = changes[0].split("@@")
#                             else:
#                                 split[0] = "NULL"
#                         else:
#                             fileData += fileLine
#                     elif split[0] == "Deleted":
#                         if deleted == None:
#                             deleted = split[1].split("/")
#                         print(f"Diff {line[9]} {deleted[11]}")
#                         if line[9] == deleted[11] and line[1] == deleted[3] and line[3] == deleted[5] and line[4] == deleted[6]:
#                             print(f"FOUND: {line[9]} {deleted[11]}")
#                             changed.append(changes[0])
#                             changes = changes[1:]
#                             if len(changes) > 0:
#                                 split = changes[0].split("@@")
#                             else:
#                                 split[0] = "NULL"
#                             deleted = None
#                         else:
#                             fileData += fileLine 
#                     elif split[0] == "Edited":
#                         if deleted == None:
#                             deleted = split[1].split("/")
#                         print(f"Diff {line[9]} {deleted[11]}")
#                         if line[9] == deleted[11] and line[1] == deleted[3] and line[3] == deleted[5] and line[4] == deleted[6]:
#                             print(f"FOUND: {line[9]} {deleted[11]} {"@@".join(split[1].split("/")[2:])}")
#                             fileData += "@@".join(split[2:]) + "\r\n"
#                             changed.append(changes[0])
#                             changes = changes[1:]
#                             if len(changes) > 0:
#                                 split = changes[0].split("@@")
#                             else:
#                                 split[0] = "NULL"
#                             deleted = None
#                         else:
#                             fileData += fileLine 
#                     else:
#                         fileData += fileLine
#                 else:
#                     fileData += fileLine
#                 if not found:
#                     fileLine = theFile.readline()
#             while len(changes) > 0:
#                 print("TEST2")
#                 if changes[0] == "":
#                     break
#                 if split[0] == "NotSynced":
#                     fileData += "@@".join(split[2:]) + "\r\n"
#                     changed.append(changes[0])
#                     changes = changes[1:]
#                     if len(changes) > 0:
#                         split = changes[0].split("@@")
#                 if split[0] == "Edited" or split[0] == "Deleted":
#                     changes = changes[1:]
#                     if len(changes) > 0:
#                         split = changes[0].split("@@")
#     except FileNotFoundError:
#         print("File not found.")
#         fileData = f"1\r\n"
#         for change in changes:
#             fileData += f"{change.split("@@", 2)[-1]}"
#         print("Creating new file.")
#         #print(fileData)
#     with open((Path(__file__).parent / "CalendarDatabase" / f"{file}"), "w", newline='') as newFile:
#         newFile.write(fileData)

#     if len(changed) > 0:
#         print(f"Changed: {changed}")
#         broadcast(f"Put\r\nFile: {file}\r\nVersion: {serverVersion}\r\n{"\r\n".join(changed)}")
#     return

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

def convertTime(time):
    split = time.split(":")
    if len(split[0]) == 1:
        split[0] = "0" + split[0]
    if split[1][2] == 'a':
        if split[0] == "12":
            return f"00:{split[1][:2]}:00"
        else:
            return f"{split[0]}:{split[1][:2]}:00"
    else:
        if split[0] == "12":
            return f"12:{split[1][:2]}:00"
        else:
            return f"{int(split[0]) + 12}:{split[1][:2]}:00"
        
def revertTime(time):
    total_seconds = int(time.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    split = time_str.split(":")
    hour = int(split[0])
    minute = split[1]
    last = 'a'
    if hour >= 12:
        last = 'p'
    if hour == 0:
        hour = 12
    elif hour >= 13:
        hour -= 12
    return f"{hour}:{minute}{last}"
    

if __name__ == "__main__":
    try:
        load_dotenv()
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = os.getenv('DB_HOST')
        port = int(os.getenv('DB_PORT'))
        database = os.getenv('DB_DATABASE')
        print(f"The test: {user}, {password}, {host}. {port}, {database}")
        
        conn = mariadb.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        conn.autocommit = True
    except mariadb.Error as e:
        print(e)
        sys.exit(1)

    cur = conn.cursor()
    print(f"This {cur}")
    cur.execute("CREATE TABLE IF NOT EXISTS Versions (" \
                "vyear SMALLINT PRIMARY KEY," \
                "version INT" \
                ")")
    cur.execute("CREATE TABLE IF NOT EXISTS Events (" \
                "eid INT AUTO_INCREMENT PRIMARY KEY," \
                "name VARCHAR(25) NOT NULL," \
                "startTime TIME NOT NULL," \
                "endTime TIME NOT NULL," \
                "day TINYINT," \
                "month TINYINT," \
                "year SMALLINT," \
                "red TINYINT UNSIGNED," \
                "green TINYINT UNSIGNED," \
                "blue TINYINT UNSIGNED," \
                "tstamp VARCHAR(19) NOT NULL," \
                "FOREIGN KEY (year) REFERENCES Versions(vyear)" \
                ")")
    cur.execute("CREATE INDEX IF NOT EXISTS event_sort ON Events (year, month, day, startTime)")
    #cur.execute("INSERT INTO Events (name, startTime, endTime, day, month, year, red, green, blue, tstamp) Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("Something", "09:30:00", "09:45:00", 30, 1, 2026, 100, 100, 100, "2026-01-25 17:33:14",))
    # with open((Path(__file__).parent / "CalendarDatabase" / "test2.txt"), "r") as theFile:
    #     fl = theFile.readline()
    #     while fl:
    #         fl = fl.split("@@")
    #         cur.execute("INSERT INTO Events (name, startTime, endTime, day, month, year, red, green, blue, tstamp) Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (fl[0], convertTime(fl[1]), convertTime(fl[2]), int(fl[3]), int(fl[4]), int(fl[5]), int(fl[6]), int(fl[7]), int(fl[8]), fl[9],))
    #         count = cur.rowcount
    #         print(count)
    #         fl = theFile.readline()

    end = [False]
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

    while not end[0]:
        try:
            connId, addrInfo = serverSocket.accept()
            connections.append(connId)
        except OSError:
            break

        if end[0]:
            break

        thread = threading.Thread(target=handleClientRecieving, args=(connId, end, cur,), daemon=True)
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
