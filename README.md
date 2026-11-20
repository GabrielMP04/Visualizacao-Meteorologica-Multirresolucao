# Visualização Meteorológica Multirresolução

Gabriel Marques Paulon · RA 113142 · Gustavo Tesche · RA 113265

Aplicação desktop desenvolvida em **Python e OpenGL 3.3** para visualização tridimensional do relevo do estado de São Paulo. O programa combina um modelo digital de elevação, uma imagem de satélite e dados meteorológicos horários de temperatura e precipitação.

## Objetivo

O projeto demonstra conceitos de Computação Gráfica aplicados a dados geográficos reais:

- construção de terreno 3D a partir de heightmaps;
- aplicação de textura Sentinel-2;
- recorte do estado por uma máscara geográfica;
- visualização temporal de temperatura e precipitação;
- seleção de nível de detalhe conforme a distância da câmera;
- iluminação, mapa de cores e neblina por shaders GLSL;
- comparação de desempenho com e sem LOD.

## Dados utilizados

| Dado | Origem | Função |
| --- | --- | --- |
| 33 arquivos GeoTIFF SRTM GL1 | [Global DEM Portal](https://globaldemportal.github.io/) | Fornecem as altitudes usadas na geometria do terreno. |
| `SP_UF_2025.json` | [Malha territorial do IBGE](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/SP/) | Define o contorno do estado de São Paulo. |
| Arquivo GRIB | [ERA5-Land](https://doi.org/10.24381/cds.e2161bac) | Contém temperatura do ar a 2 m e precipitação total em 336 horários. |
| Imagem Sentinel-2 L2A True Color | [Copernicus Browser](https://browser.dataspace.copernicus.eu/) | Fornece a textura em cores naturais aplicada ao terreno. |

O GRIB cobre o período de **1 a 14 de novembro de 2026**, em intervalos horários e com horários em UTC. A imagem Sentinel não possui georreferenciamento embutido; por isso, seu enquadramento é aproximado aos limites do estado.

## Construção da malha de São Paulo

1. Os 33 GeoTIFFs são lidos e reamostrados para uma grade regular de **513 × 513 pontos**.
2. As altitudes são normalizadas e convertidas em posições dos vértices.
3. O GeoJSON é rasterizado em uma máscara com o contorno estadual.
4. A malha é dividida em **256 patches**, organizados em 16 × 16 regiões de 32 × 32 células.
5. São calculadas as normais dos vértices para a iluminação da superfície.
6. A imagem Sentinel-2 é aplicada por coordenadas de textura.

O recorte é feito durante a fragmentação. A grade regular continua sendo usada internamente, preservando a estrutura necessária para os níveis de detalhe.

## Level of Detail

Cada patch pode ser desenhado com quatro passos de amostragem:

| Nível | Distância horizontal da câmera | Passo da malha |
| --- | ---: | ---: |
| 0 | menor que 150 | 1 célula |
| 1 | de 150 a 280 | 2 células |
| 2 | de 280 a 430 | 4 células |
| 3 | a partir de 430 | 8 células |

Patches próximos da câmera utilizam mais triângulos. Patches distantes utilizam uma representação simplificada. Saias verticais são adicionadas às bordas para reduzir a percepção de frestas entre níveis diferentes.

## Textura e shaders

O vertex shader transforma os vértices pelas matrizes de modelo, visão e projeção, envia as normais e calcula as coordenadas usadas para amostrar a textura.

O fragment shader realiza o recorte pela máscara de São Paulo, lê a textura e o campo meteorológico, converte o valor em cor, mistura as camadas conforme a opacidade e calcula iluminação e neblina.

A textura usa filtragem linear, mipmaps e limitação nas bordas para reduzir artefatos em diferentes distâncias.

## Dados meteorológicos

A temperatura é lida em kelvin e convertida para graus Celsius. A precipitação do ERA5-Land é armazenada em metros acumulados por ciclo de previsão. O programa calcula a precipitação de cada hora pela diferença entre acumulados consecutivos do mesmo ciclo e converte o resultado para milímetros.

Os campos são interpolados para a grade do terreno. Valores ausentes permanecem transparentes, permitindo que a textura continue visível onde o GRIB não possui cobertura.

Uma interface auxiliar permite selecionar temperatura ou precipitação, escolher dia e horário UTC, percorrer ou reproduzir a sequência temporal e controlar a visibilidade e a opacidade da camada.

## Execução

### Windows

1. Instale o Python 3.12 ou superior.
2. Execute `instalar_windows.bat`.
3. Execute `executar_windows.bat`.

### Linux

```bash
chmod +x instalar_linux.sh executar_linux.sh benchmark_linux.sh
./instalar_linux.sh
./executar_linux.sh
```

Em distribuições Debian ou Ubuntu, a interface pode exigir:

```bash
sudo apt install python3-tk libgl1-mesa-dri libglfw3
```

Para validar a leitura dos dados sem iniciar a visualização:

```bash
python main.py --prepare-data
```

## Controles

| Entrada | Ação |
| --- | --- |
| `W`, `A`, `S`, `D` | Mover a câmera |
| `Q` / `E` | Descer / subir |
| Botão direito + mouse | Alterar a direção da câmera |
| Roda do mouse | Ajustar a velocidade |
| `L` | Ativar ou desativar o LOD |
| `F` | Alternar preenchimento e wireframe |
| `T` | Ativar ou desativar a camada meteorológica |
| `+` / `-` | Alterar a opacidade |
| `R` | Restaurar a câmera |
| `B` | Iniciar ou encerrar a gravação de métricas |
| `F12` | Salvar uma captura em `outputs` |
| `Esc` | Encerrar o programa |

## Benchmark

O benchmark percorre a mesma trajetória de câmera com o LOD desativado e ativado. São registrados FPS, tempo por quadro, número de triângulos e quantidade de patches em cada nível.

```bash
python main.py --benchmark --seconds 12 --no-vsync
```

Os arquivos CSV e o gráfico comparativo são salvos em `outputs`.

## Configuração principal

O arquivo `config.json` contém os caminhos dos dados e os parâmetros da cena.

| Parâmetro | Valor atual |
| --- | --- |
| Fonte | `state` |
| Grade | 513 × 513 pontos |
| Tamanho dos patches | 32 × 32 células |
| Passos de LOD | 1, 2, 4 e 8 |
| Distâncias de LOD | 150, 280 e 430 |
| Escala vertical | 58 |
| Opacidade inicial | 50% |

## Estrutura do projeto

```text
.
├── main.py                  # Ponto de entrada
├── config.json              # Configuração da cena
├── shaders/                 # Vertex shader e fragment shader
├── src/
│   ├── application.py       # Janela e loop de renderização
│   ├── state_data.py        # Mosaico, recorte e leitura do GRIB
│   ├── state_controls.py    # Interface de seleção meteorológica
│   ├── terrain_cpu.py       # Geração da malha e seleção de LOD
│   ├── terrain_gl.py        # Buffers e desenho em OpenGL
│   ├── camera.py            # Câmera 3D
│   ├── shader.py            # Compilação dos shaders
│   └── metrics.py           # Coleta das métricas
├── data/sao-paulo/          # Dados geográficos e meteorológicos
├── tests/                   # Testes automatizados
└── outputs/                 # Capturas, métricas e gráficos
```

