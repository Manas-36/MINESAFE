// PN532 (red HW-147C board) + NTAG215 tags on a Seeed XIAO ESP32 (S3/C3)
// Library: "Adafruit PN532" (install from Arduino Library Manager, it pulls in Adafruit BusIO)
//
// Wiring (I2C mode, DIP switch set to I2C):
//   PN532 VCC -> XIAO 3V3
//   PN532 GND -> XIAO GND
//   PN532 SDA -> XIAO D4
//   PN532 SCL -> XIAO D5
//   PN532 IRQ -> XIAO D2
//   PN532 RST -> XIAO D3
//
// Usage: open Serial Monitor at 115200.
//   Tap a tag -> prints UID + contents of pages 4-7.
//   Type 'w' and press Enter, then tap a tag -> writes a test string to pages 4-7.

#include <Wire.h>
#include <Adafruit_PN532.h>

#define PN532_IRQ   D2
#define PN532_RESET D3

Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);   // I2C constructor

bool armWrite = false;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  nfc.begin();
  uint32_t ver = nfc.getFirmwareVersion();
  if (!ver) {
    Serial.println("PN532 not found - check wiring and DIP switch (I2C mode)");
    while (1) delay(10);
  }
  Serial.printf("Found PN5%02X, firmware %d.%d\n",
                (ver >> 24) & 0xFF, (ver >> 16) & 0xFF, (ver >> 8) & 0xFF);

  nfc.SAMConfig();   // configure to read ISO14443A tags
  Serial.println("Ready. Tap a tag. Send 'w' to arm a write.");
}

void loop() {
  // Serial command: 'w' arms a one-time write
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'w' || c == 'W') {
      armWrite = true;
      Serial.println("Write armed - tap a tag");
    }
  }

  uint8_t uid[7];
  uint8_t uidLen;
  if (!nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLen, 500)) {
    return;   // no tag this cycle
  }

  Serial.print("UID: ");
  for (uint8_t i = 0; i < uidLen; i++) Serial.printf("%02X ", uid[i]);
  Serial.println();

  if (uidLen != 7) {
    Serial.println("4-byte UID -> not an NTAG (probably MIFARE Classic)");
    delay(1000);
    return;
  }

  // NTAG215 user memory = pages 4..129 (4 bytes each).
  // Never write pages 0-3: they hold UID, lock bits and the one-time-programmable CC.
  if (armWrite) {
    const char msg[16] = "MANAS-TCET-01";   // 16 bytes -> exactly pages 4..7
    bool ok = true;
    for (uint8_t p = 0; p < 4; p++) {
      if (!nfc.ntag2xx_WritePage(4 + p, (uint8_t *)msg + p * 4)) { ok = false; break; }
    }
    Serial.println(ok ? "Written pages 4-7" : "Write failed - hold the tag still and retry");
    armWrite = false;
  }

  uint8_t buf[4];
  Serial.print("Pages 4-7: ");
  for (uint8_t p = 4; p < 8; p++) {
    if (nfc.ntag2xx_ReadPage(p, buf)) {
      for (uint8_t i = 0; i < 4; i++) Serial.print(isprint(buf[i]) ? (char)buf[i] : '.');
    } else {
      Serial.print("????");
    }
  }
  Serial.println();

  delay(1500);   // avoid re-reading the same tap repeatedly
}
