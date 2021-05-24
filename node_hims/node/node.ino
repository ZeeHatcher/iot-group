#define PIN_RST 9
#define PIN_SDA 10
#define PIN_POT A0
#define PIN_R 6
#define PIN_G 5
#define PIN_B 3

#define USE_TIMER_1     true
#define TIMER1_INTERVAL_MS  33

#define SAMPLE_SIZE 10
#define LOWER_BOUND 50
#define UPPER_BOUND 80

#include <SPI.h>
#include <MFRC522.h>
#include "TimerInterrupt.h"

MFRC522 rfid(PIN_SDA, PIN_RST); // Set up mfrc522 on the Arduino

byte nuidPICC[4];

void setup() {
  SPI.begin(); // open SPI connection
  rfid.PCD_Init(); // Initialize Proximity Coupling Device (PCD)
  Serial.begin(9600); // open serial connection

  ITimer1.init();
  
  if (!ITimer1.attachInterruptInterval(TIMER1_INTERVAL_MS, Timer1Handler))
  {
    Serial.println(F("Can't set ITimer1. Select another freq. or timer"));
  }

  pinMode(PIN_R, OUTPUT);
  pinMode(PIN_G, OUTPUT);
  pinMode(PIN_B, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    float color[3];
    
    int val = Serial.read();
    float hue = (float) constrain(map(val, 0, 100, LOWER_BOUND, UPPER_BOUND), LOWER_BOUND, UPPER_BOUND) / 100.0;

    setColor(hsv2rgb(hue, 1.0, 1.0, color));
  }
  
  // Check presence of new card
  if (!rfid.PICC_IsNewCardPresent()) {
    for (byte i = 0; i < sizeof(nuidPICC); i++) {
      nuidPICC[i] = 0;
    }

//    float color[3] = {1, 1, 1};
//    setColor(color);
    
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
    int sum = 0;

    // Sample multiple readings
    for (int i = 0; i < SAMPLE_SIZE; i++) {
      sum += analogRead(PIN_POT);
    }

    // Average to stabilize reading
    int average = sum / SAMPLE_SIZE;
    
    printHex(nuidPICC, sizeof(nuidPICC));
    Serial.print(":");
    Serial.println(average);
  }
}

/**
 * HSV-RGB conversion code from https://gist.github.com/postspectacular/2a4a8db092011c6743a7 
 */
void setColor(float *rgb) {
  analogWrite(PIN_R, (int)((1.0 - rgb[0]) * 255));
  analogWrite(PIN_G, (int)((1.0 - rgb[1]) * 255));
  analogWrite(PIN_B, (int)((1.0 - rgb[2]) * 255));  
}

float fract(float x) { return x - int(x); }

float mix(float a, float b, float t) { return a + (b - a) * t; }

float step(float e, float x) { return x < e ? 0.0 : 1.0; }

float* hsv2rgb(float h, float s, float b, float* rgb) {
  rgb[0] = b * mix(1.0, constrain(abs(fract(h + 1.0) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  rgb[1] = b * mix(1.0, constrain(abs(fract(h + 0.6666666) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  rgb[2] = b * mix(1.0, constrain(abs(fract(h + 0.3333333) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  return rgb;
}
