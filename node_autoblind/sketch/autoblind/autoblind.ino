// -------------------   LIBRARIES   ------------------------ //

#include <virtuabotixRTC.h>   // DS1302 Clock Module Library
#include <LiquidCrystal.h>    // LCD Library
#include <IRremote.h>         // Remote Control Library
#include <AccelStepper.h>     // Motor AccelStepper Library 

// ---------------------   PINS   -------------------------- //

#define LDR_INNER_PIN A0
#define LDR_OUTER_PIN A1
#define RECV_PIN 3
#define motorPin1  A5      // IN1 on the ULN2003 driver
#define motorPin2  A4      // IN2 on the ULN2003 driver
#define motorPin3  A3     // IN3 on the ULN2003 driver
#define motorPin4  A2     // IN4 on the ULN2003 driver
#define MotorInterfaceType 8

// -------------------    SENSORS    ------------------------ //

virtuabotixRTC myRTC(7, 6, 5);            // DS1302 Clock
LiquidCrystal lcd(8, 9, 10, 11, 12, 13);  // LCD Display

IRrecv irrecv(RECV_PIN);                  // IR Receiver
decode_results results;                   // -----------

int light_interior_value = 0;             //  Light Sensor 1
int light_exterior_value = 0;             //  Light Sensor 2

// Stepper motor
AccelStepper stepper = AccelStepper(MotorInterfaceType, motorPin1, motorPin3, motorPin2, motorPin4);
int ROTATION = 2 * 2038;
int MOTOR_MAX_POS = 5 * ROTATION;
int MOTOR_MIN_POS = -5 * ROTATION;
int MOTOR_INCREMENT = 0.1 * ROTATION;
int motor_pos = MOTOR_MAX_POS;            // Initial position at max pos


// -------------------   FUNCTIONS    ------------------------ //

void update_time() {
  // sec, min, hour, week, day, month, year
  myRTC.setDS1302Time(20, 59, 14, 2, 1, 6, 2021);
}

void read_light_sensor() {
  // Get light level 0-100 rounded down
  light_interior_value = analogRead(LDR_INNER_PIN) / 10;
  light_exterior_value = analogRead(LDR_OUTER_PIN) / 10;
}

void lcd_print() {
  lcd.clear();
  
  lcd.setCursor(0,0);
  lcd.print(myRTC.dayofmonth);
  lcd.print("/");
  lcd.print(myRTC.month);
  lcd.print("/");
  lcd.print(myRTC.year);
  lcd.setCursor(0,1);
  lcd.print(myRTC.hours);
  lcd.print(":");
  lcd.print(myRTC.minutes);
  lcd.print(":");
  lcd.print(myRTC.seconds);
  
  lcd.setCursor(13,0);
  lcd.print(light_interior_value);
  lcd.setCursor(13,1);
  lcd.print(light_exterior_value);
}

void receiveIR() {
  if (irrecv.decode()){
    switch(irrecv.decodedIRData.command){
      case 21:  // (+) Increase Position
        motor_pos = min(MOTOR_MAX_POS, motor_pos + MOTOR_INCREMENT);
        break;
      case 7:   // (-) Decrease Position
        motor_pos = max(MOTOR_MIN_POS, motor_pos - MOTOR_INCREMENT);
        break;
      case 64:  // (>>) Maximum Position
        motor_pos = MOTOR_MAX_POS;
        break;
      case 68:  // (<<) Minimum Position
        motor_pos = MOTOR_MIN_POS;
        break;
      default:  // Delay for LCD
        delay(200); 
        break;
      }
    irrecv.resume();
  }
  else {
    delay(200); // Delay for LCD
  }
}

void push_data() {
  Serial.print(light_interior_value);
  Serial.print(",");
  Serial.print(light_exterior_value);
  Serial.print(",");
  Serial.println(motor_pos);
}

void receive_date() {
  
}

// -------------------     SETUP     ------------------------ //

void setup() {
  // Setup the time once only and comment after
  // update_time();
  
  Serial.begin(9600);
  lcd.begin (16,2); //Initialize the LCD
  
  irrecv.enableIRIn();

  // Set the maximum steps per second:
  stepper.setMaxSpeed(1500);
  // Set the maximum acceleration in steps per second^2:
  stepper.setAcceleration(2000);
}


// -----------------------   LOOP    --------------------------- //
void loop() {
  read_light_sensor();
  myRTC.updateTime();
  receiveIR();
  
  stepper.moveTo(motor_pos);  // Set target position
  stepper.runToPosition();    // Run to position with set speed and acceleration

  lcd_print();

  push_data();
}
