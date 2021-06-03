#include "Wire.h" // For I2C
#include "LiquidCrystal_I2C.h" // Added library*
#include <Servo.h>
#define servoPin 6
#define echoPin 3
#define trigPin 2

Servo Servo1;
LiquidCrystal_I2C lcd(0x27,16,2);

const byte numChars = 50;
char receivedChars[numChars];
char *title = "Smart Door Lock ";
char *descrip = "Show your face to get in ";
char *lines[] = {title,descrip};
char *message = NULL;

long duration;
int distance;

void setup() {
  Servo1.attach(servoPin);
  pinMode(trigPin,OUTPUT);
  pinMode(echoPin,INPUT);
  lcd.begin();
  lcd.backlight();
  Serial.begin(9600);
  Servo1.write(0);
}

void loop() {
  lcd.clear();
  char rc;
  char endMarker = '\n';
  char delimeter = ',';
  static byte ndx = 0;
  int count = 0;
  while(Serial.available()>0){
    rc = Serial.read();
    if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
            ndx = numChars - 1;
        }
    }
    else {
      receivedChars[ndx] = '\0'; // terminate the string
      ndx = 0;
      byte index = 0;
      message = strtok(receivedChars,",");
      while (message != NULL){
        lines[index] = message;
//        Serial.println(message);
        index++;
        message = strtok(NULL,",");
      }
    }
  }
  lcd.setCursor(0,0);
  lcd.print(lines[0]);
  lcd.setCursor(0,1);
  lcd.print(lines[1]);
  if(strstr(lines[1],"Granted")){
    Servo1.write(90);
  }
  if(strstr(lines[1],"Denied")){
    Servo1.write(0);
  }
  for (int a =0; a<sizeof(lines);a++){
    if(strlen(lines[a]) >16){
      char temp = lines[a][0];
      for(int i = 1; i < strlen(lines[a]); i++) {        
         lines[a][i - 1] = lines[a][i];
      }
      lines[a][strlen(lines[a])-1] = temp;
    }
  }
  sensor();
}

void sensor(){
  digitalWrite(trigPin,LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin,HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin,LOW);

  duration = pulseIn(echoPin, HIGH);
  int new_distance = duration * 0.034 /2;
  if (distance != new_distance && abs(new_distance-distance) > 2){
    distance = new_distance;
    Serial.println(distance);
  }
  delay(500);
}
