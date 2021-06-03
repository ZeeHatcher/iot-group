//collects data from an analog sensor
// analog pin used to connect the sharp sensor
unsigned int pinStatus = 0; 
int led = 3;
int distance = A0;
int distVal = 0;  // variable to store the values from sensor(initially zero)
int light = A5;
int lightVal = 0;
int ledVal = 0;
boolean option = false;
boolean start = false;

char buffer[30];

void setup()
{
  Serial.begin(9600);               // starts the serial monitor
  pinMode(led,OUTPUT);
  digitalWrite(led,OUTPUT);
}
 
void loop()
{
  if(Serial.available() > 0)
  {
    pinStatus = Serial.parseInt();
    switch(pinStatus)
    {
      case 1:
        digitalWrite(led, HIGH);
        option = true;
        break;
      case 2:
        digitalWrite(led, LOW);
        option = true;
        break;
      case 3:
         start = true;
         break;
      default:
         break;
    }
  }
  
  distVal = analogRead(distance);       // reads the value of the sharp sensor
  lightVal = analogRead(light);
  ledVal = digitalRead(led);

  if(option == true)
  {
    delay(5000);
    option = false;
  }else
  {
    //sunrise = 50
    if(lightVal > 50)
    {
      digitalWrite(led, LOW);
    }else if(lightVal <= 50)
    {
      digitalWrite(led, HIGH);
    }
  
    //people walk-by
    if(ledVal == LOW and distVal <= 600 and distVal >= 300)
    {
      digitalWrite(led, HIGH);
      delay(5000);
      if(lightVal >= 100)
      {
        digitalWrite(led, LOW);
      }
    }
  }
  if(ledVal == LOW)
  {
    sprintf(buffer, "Distance, Light: %04d, %04d, %02d", distVal, lightVal, 0);
  }else if(ledVal == HIGH)
  {
    sprintf(buffer, "Distance, Light: %04d, %04d, %02d", distVal, lightVal, 1);
  } // prints the value of the sensor to the serial monitor
  Serial.println(buffer);
  delay(2000);                    // wait for this much time before printing next value
}
