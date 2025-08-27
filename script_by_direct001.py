from qgis.core import (
    QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsGeometry,
    QgsField, QgsVectorFileWriter, QgsProject, QgsPointXY
)
from PyQt6.QtCore import QVariant
import math
import re

# === CONFIGURAÇÃO ===
entrada_shp = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_pontos.shp"
saida_shp   = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_laterais_final.shp"

# carrega camada de entrada
layer = QgsVectorLayer(entrada_shp, "pontos_lote", "ogr")
if not layer.isValid():
    raise Exception("Não consegui abrir o shapefile de entrada.")

if layer.wkbType() != QgsWkbTypes.Point:
    raise Exception("A camada de entrada deve ser do tipo Ponto.")

if "direct" not in [f.name() for f in layer.fields()]:
    raise Exception("O shapefile de pontos precisa ter o campo 'direct'.")

# mapeamento direct → posição
mapa_direct = {
    "1": "Frente",
    "2": "Lateral Esquerda",
    "3": "Fundo",
    "4": "Lateral Direita",
    "5": "Fechamento"  # será filtrado no final
}

# cria camada de saída (linhas)
crs = layer.crs().toWkt()
out_layer = QgsVectorLayer("LineString?crs=" + crs, "laterais_lotes", "memory")
pr = out_layer.dataProvider()
pr.addAttributes([
    QgsField("direct", QVariant.String),
    QgsField("posicao", QVariant.String),
    QgsField("comprimento", QVariant.Double)
])
out_layer.updateFields()

# lê e ordena os pontos pelo ID
pontos = [feat for feat in layer.getFeatures()]
pontos.sort(key=lambda f: f.id())

novas_feats = []

# percorre todos os pontos consecutivos e cria linhas
for i in range(len(pontos)-1):
    p1 = pontos[i]
    p2 = pontos[i+1]

    # pega a parte numérica do direct
    direct_val = str(p1["direct"])
    chave = re.match(r"\d+", direct_val)
    if chave:
        chave = chave.group()
    else:
        chave = None

    # ignora pontos inválidos
    if chave not in mapa_direct:
        continue

    posicao = mapa_direct[chave]

    x1, y1 = p1.geometry().asPoint()
    x2, y2 = p2.geometry().asPoint()
    comprimento = math.hypot(x2 - x1, y2 - y1)

    linha = QgsFeature(out_layer.fields())
    linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
    linha.setAttributes([direct_val, posicao, comprimento])
    novas_feats.append(linha)

# === FILTRA FECHAMENTO ===
linhas_filtradas = []
for feat in novas_feats:
    direct_val = str(feat["direct"])
    chave = re.match(r"\d+", direct_val)
    if chave:
        chave = chave.group()
    else:
        chave = None

    # inclui apenas se não for fechamento
    if chave != "5":
        linhas_filtradas.append(feat)

# adiciona linhas filtradas na camada de saída
pr.addFeatures(linhas_filtradas)
out_layer.updateExtents()

# salva shapefile final
QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_shp, "utf-8", out_layer.crs(), "ESRI Shapefile"
)

# adiciona ao QGIS
QgsProject.instance().addMapLayer(out_layer)
print(f"Shapefile de laterais gerado: {saida_shp}")
