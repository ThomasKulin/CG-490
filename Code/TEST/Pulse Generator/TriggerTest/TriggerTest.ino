byte pulsePin = 3;

int onTime = 20;  //pulse duration in ms
int min_offTime = 500;  //minimum rest time between pulses
int numIterations = 0;

void setup() {
  pinMode(pulsePin, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(12, INPUT_PULLUP);
}

void loop() {
  if(digitalRead(12)==LOW){
    digitalWrite(pulsePin, HIGH);
    digitalWrite(13, HIGH);
    delay(onTime);
    digitalWrite(pulsePin, LOW);
    digitalWrite(13, LOW);
    delay(min_offTime);
  }
}
