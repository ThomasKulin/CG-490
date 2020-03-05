byte pulsePin = 3;

int onTime = 2;
int offTime = 500;
int numIterations = 0;

int iter = 0;
void setup() {
  pinMode(pulsePin, OUTPUT);
  pinMode(2, OUTPUT);
}

void loop() {
  digitalWrite(2, LOW);
  if (numIterations==0 || numIterations > iter) {
    digitalWrite(pulsePin, HIGH);
    delay(onTime);
    digitalWrite(pulsePin, LOW);
    delay(offTime);
    iter++;
  }
}
