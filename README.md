# 🗺️ Gerador de Laterais de Lotes com GeoLink

Script em **PyQGIS** que automatiza a criação de **linhas de laterais de lotes** a partir de pontos, vinculando-as a polígonos correspondentes por meio do campo `geolink`.

---

## 📌 Funcionalidades
- 🔹 Geração de **linhas** a partir de pontos (camada de entrada)  
- 🔹 Cálculo automático do **comprimento** de cada lateral  
- 🔹 Identificação da **posição** da lateral (`Frente`, `Fundo`, `Lateral Esquerda`, `Lateral Direita`)  
- 🔹 Associação das linhas ao polígono correto via campo `geolink`  
- 🔹 Exportação para shapefile (`laterais_com_geolink.shp`)  

---

## 📂 Estrutura esperada dos dados

### Camada de pontos (`amostra_lotes_pontos.shp`)
Deve conter o campo **`direct`** indicando a posição da lateral:  
- `1` → Frente  
- `2` → Lateral Esquerda  
- `3` → Fundo  
- `4` → Lateral Direita  
- `5` → Fechamento (ignorado)  

### Camada de polígonos (`amostra_lotes_shp.shp`)
- Deve conter o campo **`geolink`** que identifica cada lote.  

---

## ⚙️ Como usar
1. Abra o **QGIS** e vá em `Plugins > Python Console`.  
2. Ajuste os caminhos de entrada/saída no início do script:  

   ```python
   entrada_pontos = r"D:/data/consultorias/amostra_lotes_pontos.shp"
   poligonos_shp = r"D:/data/consultorias/amostra_lotes_shp.shp"
   saida_linhas  = r"D:/data/consultorias/laterais_com_geolink.shp"
