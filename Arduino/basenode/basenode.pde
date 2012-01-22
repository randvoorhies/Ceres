#include <SPI.h>
#include <Ethernet.h>
#include "MD5.h"

// Network globals
byte mac[]    = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
byte ip[]     = { 192,168,2,200 };
byte server[] = { 50,57,234,79 };
char hwid[]   = "1234567890";
EthernetClient client;

// Misc globals
int const lightPin = 2;
int const humidityPin = 0;
int const ledPin = 8;

void setup()
{
  pinMode(lightPin, INPUT);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  Ethernet.begin(mac, ip);

  Serial.begin(9600);

  delay(1000);

  // Blink the LED 5 times quickly to signal that setup is finished
  for(int i=0; i<5; ++i) 
  {
    digitalWrite(ledPin, !digitalRead(ledPin));
    delay(200);
  }
  digitalWrite(ledPin, HIGH);
}

void loop()
{
  Serial.println("Connecting...");
  if(client.connect(server, 10000))
  {
    // Read the light sensor
    unsigned long lightDuration = pulseIn(lightPin, HIGH, 250000);
    float lightFrequency = -1;
    if(lightDuration != 0)
      lightFrequency = 1000.0 / lightDuration;

    // Read the humidity sensor
    float humidityVoltage = analogRead(humidityPin) * 5.0 / 1024.0;
    float humidityRelative = (humidityVoltage - 0.958) / 0.0307;

    client.print("hwid : ");
    client.println(hwid);

    client.print("light : ");
    client.println(lightFrequency, 8);

    client.print("humidity : ");
    client.println(humidityRelative, 8);

    client.stop();

    digitalWrite(ledPin, LOW);
    delay(500);
  }
  else
  {
    Serial.println("Failed to connect");
  }
  digitalWrite(ledPin, HIGH);
  delay(500);
}


