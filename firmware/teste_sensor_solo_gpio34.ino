// Teste básico do módulo de umidade no ESP32
// O valor exibido é bruto: não representa porcentagem calibrada.

constexpr int PIN_SENSOR = 34;       // P34 / GPIO34
constexpr int NUM_LEITURAS = 16;
constexpr unsigned long INTERVALO_MS = 1000;

void setup() {
  Serial.begin(115200);
  delay(500);

  analogReadResolution(12);  // Leitura de 0 a 4095
  analogSetPinAttenuation(PIN_SENSOR, ADC_11db);

  Serial.println();
  Serial.println("Teste do sensor de umidade - ESP32");
  Serial.println("Leitura bruta do pino AO no GPIO34");
}

void loop() {
  uint32_t soma = 0;

  for (int i = 0; i < NUM_LEITURAS; i++) {
    soma += analogRead(PIN_SENSOR);
    delay(2);
  }

  const uint32_t media = soma / NUM_LEITURAS;

  Serial.print("AO GPIO34: ");
  Serial.print(media);
  Serial.println(" / 4095");

  delay(INTERVALO_MS);
}
