/*
 * No de ensaio de alcance LoRa — GUARDIAN-KITE
 *
 * Alvo de referencia: LilyGO T-Beam (ESP32 + SX1262 + GNSS + suporte 18650).
 * Bibliotecas: RadioLib, TinyGPSPlus, SD (cartao no slot do T-Beam).
 *
 * O que faz:
 *   - le a posicao do GNSS continuamente;
 *   - transmite um pacote curto a cada INTERVALO_MS, alternando entre os
 *     fatores de espalhamento de CICLO;
 *   - GRAVA LOCALMENTE cada transmissao no cartao SD, com posicao e SF.
 *
 * O log local nao e conveniencia, e o ponto do ensaio: quando o enlace cai, a
 * posicao nao chega ao gateway, e e exatamente essa a posicao que interessa
 * saber. Sem log no no, o ensaio nao mede o limite de alcance -- mede so ate
 * onde o gateway ja ouvia.
 *
 * O CSV gerado alimenta tools/ensaio-lora/analisar_ensaio.py sem edicao.
 *
 * ATENCAO REGULATORIA: configurar o plano AU915 (Brasil). Nao usar EU868 nem
 * US915. Potencia dentro do Ato ANATEL 14448/2017. Ver docs/05-ENSAIO-LORA.md.
 *
 * Sketch de referencia: adaptar aos pinos da sua placa e compilar antes de ir
 * a campo. Nao foi compilado no ambiente em que foi escrito.
 */

#include <RadioLib.h>
#include <TinyGPSPlus.h>
#include <SPI.h>
#include <SD.h>

// ---- pinos (T-Beam v1.1/v1.2 — CONFERIR na sua placa) ----
#define LORA_CS    18
#define LORA_DIO1  33
#define LORA_RST   23
#define LORA_BUSY  32
#define SD_CS      13
#define GPS_RX     34
#define GPS_TX     12

// ---- parametros do ensaio ----
static const float    FREQ_MHZ    = 915.2;   // dentro de 915–928 MHz (AU915)
static const float    BW_KHZ      = 125.0;
static const uint8_t  CR          = 5;       // 4/5
static const int8_t   POT_DBM     = 20;      // conduzido; ver limite do Ato 14448
static const uint8_t  CICLO[]     = {7, 9, 10, 12};
static const uint32_t INTERVALO_MS = 2000;

// Posicao do dispositivo no corpo durante este trecho do ensaio.
// Trocar entre os trechos do ensaio estatico: "no ar, mastro do barco",
// "braco", "colete", "submerso 10 cm".
static const char* POSICAO_CORPO = "braco";

SX1262 radio = new Module(LORA_CS, LORA_DIO1, LORA_RST, LORA_BUSY);
TinyGPSPlus gps;
HardwareSerial GPSSerial(1);

uint32_t seq = 0;
uint8_t  idxCiclo = 0;
File     log_;

void abrirLog() {
  if (!SD.begin(SD_CS)) {
    Serial.println("FALHA: cartao SD nao montou. NAO SEGUIR SEM LOG LOCAL.");
    return;
  }
  bool novo = !SD.exists("/no.csv");
  log_ = SD.open("/no.csv", FILE_APPEND);
  if (novo && log_) {
    log_.println("ts_utc,seq,sf,lat,lon,hdop,sats,bateria_v,posicao_corpo");
    log_.flush();
  }
}

String carimboUTC() {
  char buf[24];
  if (gps.date.isValid() && gps.time.isValid()) {
    snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02dZ",
             gps.date.year(), gps.date.month(), gps.date.day(),
             gps.time.hour(), gps.time.minute(), gps.time.second());
  } else {
    snprintf(buf, sizeof(buf), "sem-fix-%lu", (unsigned long)millis() / 1000);
  }
  return String(buf);
}

void setup() {
  Serial.begin(115200);
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);
  abrirLog();

  int st = radio.begin(FREQ_MHZ, BW_KHZ, CICLO[0], CR, RADIOLIB_SX126X_SYNC_WORD_PRIVATE, POT_DBM);
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("FALHA no radio: %d\n", st);
    while (true) delay(1000);
  }
  radio.setCurrentLimit(140.0);
  Serial.println("no de ensaio pronto");
}

void loop() {
  // mantem o parser de GNSS alimentado enquanto espera o proximo envio
  uint32_t t0 = millis();
  while (millis() - t0 < INTERVALO_MS) {
    while (GPSSerial.available()) gps.encode(GPSSerial.read());
    delay(2);
  }

  uint8_t sf = CICLO[idxCiclo];
  idxCiclo = (idxCiclo + 1) % (sizeof(CICLO) / sizeof(CICLO[0]));
  radio.setSpreadingFactor(sf);

  // pacote minimo: o gateway so precisa casar seq e sf; a posicao vem do log local
  char payload[32];
  snprintf(payload, sizeof(payload), "E,%lu,%u", (unsigned long)seq, sf);

  bool ok = (radio.transmit((uint8_t*)payload, strlen(payload)) == RADIOLIB_ERR_NONE);

  float lat = gps.location.isValid() ? gps.location.lat() : 0.0;
  float lon = gps.location.isValid() ? gps.location.lng() : 0.0;
  float hdop = gps.hdop.isValid() ? gps.hdop.hdop() : 99.9;
  uint32_t sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
  float vbat = analogRead(35) * 2.0 * 3.3 / 4095.0;   // divisor do T-Beam

  if (log_) {
    log_.printf("%s,%lu,SF%u,%.6f,%.6f,%.1f,%lu,%.2f,%s\n",
                carimboUTC().c_str(), (unsigned long)seq, sf,
                lat, lon, hdop, (unsigned long)sats, vbat, POSICAO_CORPO);
    if (seq % 10 == 0) log_.flush();          // sobrevive a queda de energia
  }

  Serial.printf("seq=%lu SF%u tx=%s sats=%lu %.5f,%.5f\n",
                (unsigned long)seq, sf, ok ? "ok" : "ERRO",
                (unsigned long)sats, lat, lon);
  seq++;
}
