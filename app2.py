from qgis.core import (
    QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsGeometry,
    QgsField, QgsVectorFileWriter, QgsProject, QgsPointXY
)
from PyQt6.QtCore import QVariant
import math, os

# === CONFIGURAÇÃO ===
entrada_shp = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_shp.shp"
saida_shp   = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_shp_laterais_v003.shp"

# carrega camada
layer = QgsVectorLayer(entrada_shp, "lotes", "ogr")
if not layer.isValid():
    raise Exception("Não consegui abrir o shapefile de entrada.")

if layer.wkbType() not in [QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon]:
    raise Exception("A camada selecionada não é poligonal.")

# identifica campo ID
id_field = None
for cand in ["id","ID","Id","lote","Lote","LOT","COD","CODIGO"]:
    if cand in [f.name() for f in layer.fields()]:
        id_field = cand
        break

# função para classificar lateral com base em coordenadas
def classificar_lados(lados):
    """
    lados: lista de tuplas [(x1,y1,x2,y2), ...]
    Retorna lista de posicoes ["Frente", "Fundo", "Esquerda", "Direita"]
    """
    # calcula Y médio de cada lado
    y_medios = [( (y1+y2)/2, idx) for idx,(x1,y1,x2,y2) in enumerate(lados)]
    y_medios.sort(key=lambda x: x[0])  # menor Y primeiro
    frente_idx = y_medios[0][1]
    fundo_idx = y_medios[-1][1]

    posicoes = [None]*len(lados)
    for i in range(len(lados)):
        if i == frente_idx:
            posicoes[i] = "Frente"
        elif i == fundo_idx:
            posicoes[i] = "Fundo"
        else:
            # determina Esquerda/Direita pelo ângulo do segmento
            x1,y1,x2,y2 = lados[i]
            dx = x2 - x1
            dy = y2 - y1
            ang = math.degrees(math.atan2(dy, dx))
            if ang > 0:
                posicoes[i] = "Direita"
            else:
                posicoes[i] = "Esquerda"
    return posicoes

# cria camada de saída
crs = layer.crs().toWkt()
out_layer = QgsVectorLayer("LineString?crs=" + crs, "laterais_lotes", "memory")
pr = out_layer.dataProvider()
pr.addAttributes([
    QgsField("id_lote", QVariant.String),
    QgsField("comprimento", QVariant.Double),
    QgsField("posicao", QVariant.String)
])
out_layer.updateFields()
novas_feats = []

# processa cada lote
for f_idx, feat in enumerate(layer.getFeatures()):
    lote_id = feat[id_field] if id_field else f"L{f_idx+1}"
    geom = feat.geometry()
    if geom.isEmpty():
        continue
    if not geom.isGeosValid():
        geom = geom.buffer(0)

    if geom.isMultipart():
        polygons = geom.asMultiPolygon()
    else:
        polygons = [geom.asPolygon()]

    for part in polygons:
        if not part:
            continue
        exterior = part[0]
        lados = []
        for i in range(len(exterior)-1):
            x1,y1 = exterior[i]
            x2,y2 = exterior[i+1]
            lados.append((x1,y1,x2,y2))

        posicoes = classificar_lados(lados)

        for i,(x1,y1,x2,y2) in enumerate(lados):
            comprimento = math.hypot(x2-x1, y2-y1)
            linha = QgsFeature(out_layer.fields())
            linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1,y1), QgsPointXY(x2,y2)]))
            linha.setAttributes([str(lote_id), comprimento, posicoes[i]])
            novas_feats.append(linha)

pr.addFeatures(novas_feats)
out_layer.updateExtents()

# salva shapefile único
QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_shp, "utf-8", out_layer.crs(), "ESRI Shapefile"
)

# adiciona ao projeto QGIS
QgsProject.instance().addMapLayer(out_layer)
print(f"Shapefile único gerado com todas as laterais: {saida_shp}")
