# daa_project

##esp8266 code

```
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN D3
#define SS_PIN D4
#define GREEN_LED D1
#define RED_LED D2

const char* ssid = "CMF";
const char* password = "deepika2005";

// Flask server IP and endpoint (using port 80)
const char* server = "http://192.168.39.120/rfid";

MFRC522 mfrc522(SS_PIN, RST_PIN);

// List of authorized UIDs
const byte authorizedUIDs[][4] = {
  {0xE7, 0x86, 0x4A, 0xCA},
  {0x04, 0xAE, 0xB5, 0xA3},
  {0xE7, 0xCF, 0xD, 0xCA},
  {0xA7, 0x33, 0x5D, 0xCA},
  {0xF7, 0xFE, 0x9D, 0xCA},
  {0x97, 0x37, 0x17, 0xCA}
};
const int totalAuthorized = sizeof(authorizedUIDs) / sizeof(authorizedUIDs[0]);

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");

  SPI.begin();
  mfrc522.PCD_Init();

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  String uidStr = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidStr += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) uidStr += "-";
  }

  Serial.println("Scanned UID: " + uidStr);

  if (isAuthorized(mfrc522.uid.uidByte, mfrc522.uid.size)) {
    Serial.println("Access Granted");
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
  } else {
    Serial.println("Access Denied");
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
  }

  sendToFlask(uidStr);
  delay(2000);

  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

bool isAuthorized(byte *uid, byte uidSize) {
  for (int i = 0; i < totalAuthorized; i++) {
    bool match = true;
    for (int j = 0; j < uidSize; j++) {
      if (authorizedUIDs[i][j] != uid[j]) {
        match = false;
        break;
      }
    }
    if (match) return true;
  }
  return false;
}

void sendToFlask(String uidStr) {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;
    http.setTimeout(5000);  // Set timeout to 5 seconds
    http.begin(client, server);
    http.addHeader("Content-Type", "application/json");
    String payload = "{\"uid\":\"" + uidStr + "\"}";
    int httpResponseCode = http.POST(payload);
    // Retry once if it fails
    if (httpResponseCode <= 0) {
      Serial.println("POST failed, retrying in 2s...");
      delay(2000);
      httpResponseCode = http.POST(payload);
    }
    Serial.print("POST response: ");
    Serial.println(httpResponseCode);
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Server response: " + response);
    }
    http.end();
  } else {
    Serial.println("WiFi not connected");
  }
}
```
