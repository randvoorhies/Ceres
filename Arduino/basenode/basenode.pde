#include <SPI.h>
#include <Ethernet.h>
#include "MD5.h"

byte mac[]    = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
byte ip[]     = { 192,168,1,2 };
byte server[] = { 192,168,1,1 };

char key[] = "s#lkj3lD#$FmD/23lr&k.?o8c0)(*FDE)G#ndYR^ 3i9298#";

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
  //char input[] = "Hello, this is dog";
  //char md5[33];
  //computeMD5(&input[0], &md5[0]);
  //Serial.println(md5);

  if(client.connect())
  {
    client.println(counter);
    client.stop();
    Serial.print("Connection success: ");
    Serial.println(counter);
  }
  else
  {
    Serial.println("Failed to connect");
  }
  counter = counter+1;
  if(counter > 100) counter = 0;
  delay(1000);
}


