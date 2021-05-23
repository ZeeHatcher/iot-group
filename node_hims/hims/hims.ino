#define PIN_RST 9
#define PIN_SDA 10
#define PIN_POT A0
#define PIN_BTN 2

#define USE_TIMER_1     true
#define TIMER1_INTERVAL_MS  5000

#include <SPI.h>
#include <MFRC522.h>
#include "TimerInterrupt.h"

MFRC522 rfid(PIN_SDA, PIN_RST); // Set up mfrc522 on the Arduino

byte nuidPICC[4];
boolean isOn;

void setup() {
  SPI.begin(); // open SPI connection
  rfid.PCD_Init(); // Initialize Proximity Coupling Device (PCD)
  Serial.begin(9600); // open serial connection

  ITimer1.init();
  
  if (!ITimer1.attachInterruptInterval(TIMER1_INTERVAL_MS, Timer1Handler))
  {
    Serial.println(F("Can't set ITimer1. Select another freq. or timer"));
  }
  
  pinMode(PIN_BTN, INPUT_PULLUP);
}

void loop() {
  // Get button state
  isOn = digitalRead(PIN_BTN);
  
  // Check presence of new card
  if (!rfid.PICC_IsNewCardPresent()) {
    for (byte i = 0; i < sizeof(nuidPICC); i++) {
      nuidPICC[i] = 0;
    }
    return;
  }
  
  if (!rfid.PICC_ReadCardSerial()) return;

  // Assign new value to NUID if different
  if (rfid.uid.uidByte[0] != nuidPICC[0] || 
    rfid.uid.uidByte[1] != nuidPICC[1] || 
    rfid.uid.uidByte[2] != nuidPICC[2] || 
    rfid.uid.uidByte[3] != nuidPICC[3] ) {

    // Store NUID into nuidPICC array
    for (byte i = 0; i < sizeof(nuidPICC); i++) {
      nuidPICC[i] = rfid.uid.uidByte[i];
    }
  }
}

/**
 * Helper routine to dump a byte array as hex values to Serial. 
 */
void printHex(byte *buffer, byte bufferSize) {
  for (byte i = 0; i < bufferSize; i++) {
    Serial.print(buffer[i], HEX);
  }
}

void Timer1Handler() {
  // Print recorded NUID if not "empty" / is not filled with 0s
  if (nuidPICC[0] || nuidPICC[1] || nuidPICC[2] || nuidPICC[3]) {
    printHex(nuidPICC, sizeof(nuidPICC));
    Serial.print(":");
    Serial.print(isOn ? "on" : "off");
    Serial.print(":");
    Serial.println(analogRead(PIN_POT));
  }
}
