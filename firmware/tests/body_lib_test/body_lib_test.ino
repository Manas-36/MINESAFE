// =====================================================================
//  MineSafe - BODY UNIT CROSS-CHECK WITH STANDARD LIBRARIES
//  Same job as body_sensor_test, but every sensor is read with the well-known
//  Arduino library instead of our own driver. If THIS sketch also finds nothing,
//  the problem is the wiring / power, not our code.
//
//  Board : ESP32-C6-WROOM-1 DevKit -> "ESP32C6 Dev Module" (also ESP32-S3 / XIAO C6)
//  Libraries (Arduino IDE -> Library Manager, search the exact name):
//    "Adafruit BMP085 Library"  by Adafruit   (installs "Adafruit Unified Sensor" + "Adafruit BusIO")
//    "MPU6050"                  by Electronic Cats
//    "OneWire"                  by Paul Stoffregen
//    "DallasTemperature"        by Miles Burton
//    "SparkFun MAX3010x Pulse and Proximity Sensor Library"   (only if you fit a MAX30102)
//  NOTE: library examples call Wire.begin() with NO pins = GPIO23/22 on the C6 DevKit.
//        Our wiring is SDA GPIO6 / SCL GPIO7, so this sketch calls Wire.begin(6, 7).
// =====================================================================
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <MPU6050.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <MAX30105.h>

// ---- print to BOTH the USB socket and the UART/COM socket, so the Serial Monitor
//      shows output whatever the "USB CDC On Boot" setting or the socket you use ----
#if ARDUINO_USB_MODE && SOC_USB_SERIAL_JTAG_SUPPORTED
#include "HWCDC.h"
#if ARDUINO_USB_CDC_ON_BOOT
  #define USB_PORT HWCDCSerial
#else
  HWCDC UsbPort;
  #define USB_PORT UsbPort
#endif
class DualSerial : public Print {
 public:
  void begin(unsigned long baud) {
    Serial0.begin(baud);
    USB_PORT.begin();
    USB_PORT.setTxTimeoutMs(0);             // never block when no USB monitor is open
  }
  size_t write(uint8_t c) override { Serial0.write(c); if (USB_PORT) USB_PORT.write(c); return 1; }
  size_t write(const uint8_t* b, size_t n) override { Serial0.write(b, n); if (USB_PORT) USB_PORT.write(b, n); return n; }
  int available() { return Serial0.available() + USB_PORT.available(); }
  int read() { return Serial0.available() ? Serial0.read() : USB_PORT.read(); }
  operator bool() { return (bool)USB_PORT; }
};
DualSerial DualOut;
#undef Serial
#define Serial DualOut
#endif

#if CONFIG_IDF_TARGET_ESP32C6 && !defined(ARDUINO_XIAO_ESP32C6)
  #define I2C_SDA 6
  #define I2C_SCL 7
  #define DS_PIN 10
  #define PULSE_PIN 2
#elif CONFIG_IDF_TARGET_ESP32C6
  #define I2C_SDA 22
  #define I2C_SCL 23
  #define DS_PIN 21
  #define PULSE_PIN 0
#else
  #define I2C_SDA 8
  #define I2C_SCL 9
  #define DS_PIN 7
  #define PULSE_PIN 4
#endif

Adafruit_BMP085   bmp;
MPU6050           mpu;
OneWire           ow(DS_PIN);
DallasTemperature ds(&ow);
MAX30105          ppg;
bool bmpOk, mpuOk, dsOk, ppgOk;

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 4000) delay(10);
  delay(300);
  Serial.printf("\n==== Library cross-check  SDA GPIO%d  SCL GPIO%d  DS18B20 GPIO%d  HW-827 GPIO%d ====\n",
                I2C_SDA, I2C_SCL, DS_PIN, PULSE_PIN);
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);

  Serial.print("I2C scan:");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) { Wire.beginTransmission(a); if (Wire.endTransmission() == 0) { Serial.printf(" 0x%02X", a); n++; } }
  Serial.println(n ? "" : " nothing");

  mpu.initialize();
  uint8_t who = mpu.getDeviceID();
  mpuOk = who != 0 && who != 0x3F;               // 0 / 0x3F = no answer on the bus
  Serial.printf("MPU6050 (Electronic Cats): %s  (device id 0x%02X%s)\n", mpuOk ? "FOUND" : "NOT FOUND", who,
                mpu.testConnection() ? "" : mpuOk ? ", clone chip - readings still fine" : "");

  bmpOk = bmp.begin(BMP085_STANDARD, &Wire);
  Serial.printf("BMP180 (Adafruit BMP085): %s\n", bmpOk ? "FOUND" : "NOT FOUND");

  ds.begin();
  dsOk = ds.getDeviceCount() > 0;
  Serial.printf("DS18B20 (DallasTemperature): %d device(s) on GPIO%d\n", ds.getDeviceCount(), DS_PIN);

  ppgOk = ppg.begin(Wire, I2C_SPEED_STANDARD);
  if (ppgOk) { ppg.setup(0x1F, 4, 2, 100, 411, 4096); Serial.println("MAX30102 (SparkFun): FOUND"); }
  else Serial.println("MAX30102 (SparkFun): not fitted (optional)");
  analogSetPinAttenuation(PULSE_PIN, ADC_11db);
  Serial.println();
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < 1000) return;
  last = millis();
  if (mpuOk) {
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);           // default range: +-2 g, +-250 deg/s
    Serial.printf("acc %+.2f %+.2f %+.2f g  gyro %+6.1f %+6.1f %+6.1f dps | ",
                  ax / 16384.0, ay / 16384.0, az / 16384.0, gx / 131.0, gy / 131.0, gz / 131.0);
  }
  if (bmpOk) Serial.printf("BMP %.1f C %.1f hPa | ", bmp.readTemperature(), bmp.readPressure() / 100.0);
  if (dsOk) { ds.requestTemperatures(); Serial.printf("skin %.2f C | ", ds.getTempCByIndex(0)); }
  if (ppgOk) Serial.printf("IR %lu | ", (unsigned long)ppg.getIR());
  Serial.printf("pulse %d mV\n", (int)analogReadMilliVolts(PULSE_PIN));
}
