'''
simple UDP client that receives packets on port 5006
used with udp_file_sender.py for unicast packets
'''

import sys
import select
UDP_IP = "::"
UDP_PORT =5006
timeout = 3
import random
import string
import socket
import time

#open the socket
sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind((UDP_IP,UDP_PORT))


count = 0
first_data_added = 0
#file_name = ""
#file_name = ''.join(random.choice(string.lowercase) for x in range(5))
#print file_name

while True:
    #old code, ignore first true loop
    while True:
        #reads the first 1024 bytes from the socket
        data, addr = sock.recvfrom(1024)

        #if there are no bytes then nothing arrived yet, if the first bytes arrive:
        if data:
            #create a random filename
            file_name = ''.join(random.choice(string.lowercase) for x in range(5))
            file_name = file_name + ".jpg"

            print file_name

            #dump it into the filedump dir. for ease of deleting testfiles
            path_to_file = "/root/filedump/"+file_name

        # open the new file that has been created
        f = open(path_to_file, 'wb')

        # add the first 1024 bytes that arrived and start the timer
        if first_data_added == 0:
            f.write(data)
            print "added first data"
            first_data_added = 1
            count = count+1
            filesize = len(data)
            start = time.time()
            end = time.time()
        #print file_name
        while True:

            #while there is data on the socket continue to receive and write to the new file
            ready = select.select([sock], [], [], timeout)
            if ready[0]:
                data, addr = sock.recvfrom(1024)
                f.write(data)
                filesize = filesize + len(data)
                print "packet number: ",count,"with packet length: ",len(data)," total file size:", filesize," current time:", time.time()-start
                end = time.time()
                count = count+1
                #filesize = filesize + len(data)

            #if there is no more data coming then stop the timer and the current transmission.
            else:
                print "finished with:%s" % file_name
                print "file can be found in filedump/%s" % file_name

                print "total time:", end-start
                f.close()

                #sock.close()
                count = 1
                filesize = 0
                first_data_added = 0
                break
                #sys.exit()
