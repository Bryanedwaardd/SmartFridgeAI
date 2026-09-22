
int led_pin = 2;
int magSens_pin = 8;

void setup() {
  Serial.begin(9600);
  pinMode(magSens_pin, INPUT);
  pinMode(led_pin, OUTPUT);  
}

void loop() {
  // put your main code here, to run repeatedly:
  int status = digitalRead(magSens_pin); 
  
  if (status == 0) {
    Serial.println("~OPEN");
    digitalWrite(led_pin, HIGH);
  } else {
    Serial.println("~CLOSED");
    digitalWrite(led_pin, LOW);
  }
  
  delay(500);
}