#🗺️ Gerador de Laterais de Lotes com GeoLink

Este repositório contém um script em PyQGIS que automatiza a criação de linhas de laterais de lotes a partir de pontos, vinculando-as a polígonos correspondentes por meio de um campo identificador chamado geolink.

📌 Funcionalidades

Geração de linhas a partir de pontos (camada de entrada).

Cálculo automático do comprimento de cada lateral.

Identificação da posição da lateral (Frente, Fundo, Lateral Esquerda, Lateral Direita).

Associação das linhas ao polígono correto via campo geolink.

Exportação para um novo shapefile (laterais_com_geolink.shp).

📂 Estrutura esperada dos dados
Camada de pontos (amostra_lotes_pontos.shp)

Deve conter o campo direct indicando a posição da lateral:

1 → Frente

2 → Lateral Esquerda

3 → Fundo

4 → Lateral Direita

5 → Fechamento (ignorado)

Camada de polígonos (amostra_lotes_shp.shp)

Deve conter o campo geolink que identifica cada lote.

⚙️ Como usar

Abra o QGIS com o Python Console habilitado.

Ajuste os caminhos de entrada/saída no início do script:

entrada_pontos = r"D:/data/consultorias/amostra_lotes_pontos.shp"
poligonos_shp = r"D:/data/consultorias/amostra_lotes_shp.shp"
saida_linhas   = r"D:/data/consultorias/laterais_com_geolink.shp"


Execute o script no console do QGIS.

O shapefile de saída será criado com as laterais e adicionado ao projeto.

📦 Dependências

QGIS
 (3.x ou superior)

PyQt6 (incluso no QGIS)

🛠️ Atributos da camada de saída

direct → Código da lateral (1–4).

posicao → Nome da lateral (Frente, Fundo, Lateral Esquerda, Lateral Direita).

comprimento → Comprimento da linha em unidades do CRS.

geolink → Código herdado do polígono correspondente.

🧑‍💻 Autor

John Wesley Ribeiro
🔗 Currículo Lattes

📖 Licença

Este projeto é distribuído sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.
