#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "env.h"

#define ENDPOINT "ecse3038-project.onrender.com"

#define FAN_PIN 22
#define LIGHT_PIN 23
#define PRESENCE_PIN 24

float getTemperature()
{
  return random(21.1, 33.1);
}

bool getPresence()
{
  return random(0, 1);
}

void setup()
{
  Serial.begin(9600);

  pinMode(FAN_PIN, OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);

  // WiFi_SSID and WIFI_PASS should be stored in the env.h
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("");
  // Connect to WiFi
  Serial.println("Connecting");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop()
{
  // Check WiFi connection status
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("");
    Serial.println("");
    HTTPClient http;

    // Establish a connection to the server
    String url = "https://" + String(ENDPOINT) + "/info";
    http.begin(url);
    http.addHeader("Content-type", "application/json");

    StaticJsonDocument<1024> docPut;
    String httpRequestData;

    docPut["temperature"] = getTemperature();
    docPut["presence"] = getPresence();

    serializeJson(docPut, httpRequestData);

    // Send HTTP POST request
    int httpResponseCode = http.POST(httpRequestData);
    String httpResponse;

    if (httpResponseCode > 0)
    {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);

      Serial.print("HTTP Response from server: ");
      httpResponse = http.getString();
      Serial.println(httpResponse);
    }
    else
    {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();

    url = "https://" + String(ENDPOINT) + "/state";
    http.begin(url);
    httpResponseCode = http.GET();

    Serial.println("");
    Serial.println("");

    if (httpResponseCode > 0)
    {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);

      Serial.print("Response from server: ");
      httpResponse = http.getString();
      Serial.println(httpResponse);
    }
    else
    {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    StaticJsonDocument<1024> docGet;

    DeserializationError error = deserializeJson(docGet, httpResponse);

    if (error)
    {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }

    bool fanState = docGet["fan"];
    bool lightState = docGet["light"];
    bool presenceState = docGet["presence"];

    digitalWrite(FAN_PIN, fanState);
    digitalWrite(LIGHT_PIN, lightState);
    digitalWrite(PRESENCE_PIN, presenceState);

    // Free resources
    http.end();
  }
  else
  {
    Serial.println("WiFi Disconnected");
  }
}
