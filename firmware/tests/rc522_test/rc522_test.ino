// RC522 (HW-147C board, I2C mode) test for XIAO ESP32-C6 - reader ONLY, no OLED
//   Reader: GND->GND  VCC->3V3  SDA->D4  SCL->D5   DIP: 1 ON, 2 OFF
//   Library: RFID_MFRC522v2
//   Serial Monitor 115200. Every second it prints whether the reader still answers.
//   Tap an NTAG215 flat on the white coil: prints the UID and pages 4..7.
#include <Wire.h>
#include <MFRC522v2.h>
#include <MFRC522DriverI2C.h>

MFRC522DriverI2C drv{0x28, Wire};
MFRC522 rfid{drv};
uint32_t okCount = 0, failCount = 0;

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin();
  Wire.setClock(100000);            // slow = more tolerant of long wires / breadboards
  Wire.setTimeOut(50);

  Wire.beginTransmission(0x28);
  Serial.printf("Reader at 0x28: %s\n", Wire.endTransmission() == 0 ? "answers" : "NO ANSWER");

  rfid.PCD_Init();
  delay(50);
  uint8_t v = drv.PCD_ReadRegister(MFRC522Constants::PCD_Register::VersionReg);
  Serial.printf("Version register: 0x%02X  (0x91/0x92 = NXP RC522, 0x88/0xB2 = FM17522 clone, 0x00/0xFF = no reply)\n", v);
  rfid.PCD_SetAntennaGain(MFRC522Constants::RxGain_max);   // maximum receive gain = best range
  Serial.printf("Antenna gain set to max (reg 0x%02X). Tap a tag...\n", rfid.PCD_GetAntennaGain());
}

void loop() {
  static uint32_t lastPing = 0;
  if (millis() - lastPing > 1000) {
    lastPing = millis();
    Wire.beginTransmission(0x28);
    (Wire.endTransmission() == 0 ? okCount : failCount)++;
    Serial.printf("reader ping ok=%lu fail=%lu\n", (unsigned long)okCount, (unsigned long)failCount);
  }

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    Serial.print("TAG UID: ");
    for (byte i = 0; i < rfid.uid.size; i++) Serial.printf("%02X", rfid.uid.uidByte[i]);
    Serial.printf("  (%u bytes)\n", rfid.uid.size);
    byte buf[18], size = sizeof(buf);
    if (rfid.MIFARE_Read(4, buf, &size) == MFRC522Constants::STATUS_OK) {
      Serial.print("Pages 4-7: ");
      for (int i = 0; i < 16; i++) Serial.print(isprint(buf[i]) ? (char)buf[i] : '.');
      Serial.println();
    } else Serial.println("Read of pages 4-7 failed");
    rfid.PICC_HaltA();
  }
  delay(50);
}
