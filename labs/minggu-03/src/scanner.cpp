// Lab-2 Eksperimen 1: pemindai alamat bus I2C (Listing 1 modul Minggu 3)
#include <Arduino.h>
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);  // SDA = GPIO 21, SCL = GPIO 22
  Serial.println("\n--- Memindai Peranti pada Bus I2C ESP32 ---");
  byte hitung = 0;
  for (byte alamat = 1; alamat < 127; alamat++) {
    Wire.beginTransmission(alamat);
    if (Wire.endTransmission() == 0) {
      const char* nama = (alamat == 0x76 || alamat == 0x77) ? "BMP280/BME280"
                       : (alamat == 0x3C || alamat == 0x3D) ? "OLED SSD1306"
                       : (alamat == 0x68) ? "MPU6050" : "tidak dikenal";
      Serial.printf("Peranti I2C ditemukan pada alamat: 0x%02X (%s)\n", alamat, nama);
      hitung++;
    }
  }
  Serial.printf("Pemindaian selesai. Total peranti ditemukan: %d\n", hitung);
}

void loop() {}
