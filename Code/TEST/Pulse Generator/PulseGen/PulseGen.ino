byte pulsePin = 3;

int onTime = 2;
int offTime = 500;
int numIterations = 0;

int iter = 0;
void setup() {
  pinMode(pulsePin, OUTPUT);
  pinMode(13, OUTPUT);
}

void loop() {
  if (numIterations==0 || numIterations > iter) {
    digitalWrite(pulsePin, HIGH);
    digitalWrite(13, HIGH);
    delay(onTime);
    digitalWrite(pulsePin, LOW);
    digitalWrite(13, LOW);
    delay(offTime);
    iter++;
  }
}
