Change the button bindings based on these conditions:

Button bindings:
    Pre Start:
        Button 1 - Start timer
    After Start:
        Button 1 
        Button 2 - Individual recall (one hoot on horn)
        Button 3 - General recall (two hoots then reset the time and wait for the start button)
    After 20 seconds from the start of the race:
        Button 1 - Record lap time
        Button 2 - Record finish time
        Button 3 - Shorten course (two hoots on horn)

Send a packet when changing them structured like this:
{"packet-type" : "update-bindings", "binings" : {"button1" : "Button 1 label", "button2" : "Button 2 label", "button3" : "Button 3 label"}}