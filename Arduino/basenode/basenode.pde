#include <SPI.h>
#include <Ethernet.h>
#include "MD5.h"

byte mac[]    = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
byte ip[]     = { 192,168,1,2 };
byte server[] = { 192,168,1,1 };

char hwid[] = "1234567890";

Client client(server, 10000);

int counter;
void setup()
{
  counter = 0;
  Ethernet.begin(mac, ip);
  Serial.begin(9600);
  delay(1000);
}

void loop()
{
  if(client.connect())
  {
    client.print("hwid : ");
    client.println(hwid);

    client.print("0 : ");
    client.println(counter);
    client.stop();
  }
  else
  {
    Serial.println("Failed to connect");
  }

  counter = counter+1;
  if(counter > 100) counter = 0;
  delay(500);
}


