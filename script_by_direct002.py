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
    QgsField("comprimento", QVariant.Double),
    QgsField("medida", QVariant.Double)  # nova coluna para medida do segmento
])
out_layer.updateFields()

# lê e ordena os pontos pelo ID
pontos = [feat for feat in layer.getFeatures()]
pontos.sort(key=lambda f: f.id())

novas_feats = []

# dicionário para totalizar medidas por lateral
totais = {pos: 0 for pos in ["Frente", "Lateral Esquerda", "Fundo", "Lateral Direita"]}

# percorre pontos consecutivos
for i in range(len(pontos)-1):
    p1 = pontos[i]
    p2 = pontos[i+1]

    direct_val = str(p1["direct"])
    chave = re.match(r"\d+", direct_val)
    if chave:
        chave = chave.group()
    else:
        continue  # ignora pontos inválidos

    # ignora fechamento
    if chave not in mapa_direct or chave == "5":
        continue

    posicao = mapa_direct[chave]

    x1, y1 = p1.geometry().asPoint()
    x2, y2 = p2.geometry().asPoint()
    comprimento = math.hypot(x2 - x1, y2 - y1)

    # soma o comprimento no total da lateral
    totais[posicao] += comprimento

    # cria feature da linha
    linha = QgsFeature(out_layer.fields())
    linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
    linha.setAttributes([direct_val, posicao, comprimento, comprimento])
    novas_feats.append(linha)

# adiciona todas as linhas na camada de saída
pr.addFeatures(novas_feats)
out_layer.updateExtents()

# salva shapefile final
QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_shp, "utf-8", out_layer.crs(), "ESRI Shapefile"
)

# adiciona ao QGIS
QgsProject.instance().addMapLayer(out_layer)

# imprime totais por lateral
print("===== MEDIDAS TOTAIS POR LATERAL =====")
for lateral, total in totais.items():
    print(f"{lateral}: {total:.2f} unidades")

print(f"\nShapefile de laterais gerado: {saida_shp}")
