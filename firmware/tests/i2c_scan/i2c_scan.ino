// I2C scanner for XIAO ESP32-C6 - SDA = D4, SCL = D5
// Open Serial Monitor at 115200. Scans every 2 s.
// Expect: 0x24 = PN532, 0x3C = OLED
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin();              // D4 / D5 on the XIAO
  Wire.setClock(100000);     // slow and safe for the PN532
}

void loop() {
  Serial.print("Found: ");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("0x%02X ", a);
      n++;
    }
  }
  Serial.println(n ? "" : "nothing - check wires");
  delay(2000);
}
