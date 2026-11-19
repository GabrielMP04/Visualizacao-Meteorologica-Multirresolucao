# Visualização Meteorológica Multirresolução

Gabriel Marques Paulon · RA 113142

Gustavo Tesche · RA 113265

Aplicação desktop em **Python e OpenGL 3.3** que transforma um modelo digital de elevação em um terreno 3D, aplica uma imagem Sentinel-2 à superfície e permite sobrepor a temperatura média do ar. A mesma cena pode ser renderizada com uma malha uniforme ou com seleção automática de níveis de detalhe (LOD).

## O que está implementado

- Câmera 3D livre com projeção em perspectiva.
- Terreno real do SRTM GL1, reamostrado de 3.601 × 3.601 para 513 × 513 pontos.
- Textura Sentinel-2 em cor natural aplicada à malha, com filtragem linear e mipmaps.
- Temperatura média calculada por localização a partir de 288 horários do ERA5-Land. A camada pode ser ligada e ter sua opacidade ajustada.
- Divisão do terreno em 16 × 16 patches, com passos de amostragem de 1, 2, 4 e 8 células. A distância horizontal até a câmera determina o nível.
- Saias nas bordas dos patches para disfarçar frestas entre níveis e quatro buffers de índices compartilhados entre os patches.
- Modos **SEM LOD** e **COM LOD**, visualização da malha em wireframe e shaders GLSL para textura, paleta térmica, iluminação e neblina.
- Contador de FPS, triângulos e patches por nível, gravação de métricas, benchmark automático e captura de tela.

## Início rápido no Windows

1. Instale o [Python 3.12](https://www.python.org/downloads/) e marque **Add Python to PATH**.
2. Execute `instalar_windows.bat` na pasta do projeto. Se já havia uma instalação anterior, execute esse instalador para incluir o Rasterio.
3. Execute `executar_windows.bat` para abrir a visualização.
4. Execute `benchmark_windows.bat` para comparar os dois modos de renderização.

O instalador cria o ambiente virtual `.venv` e instala os pacotes de `requirements.txt`. A aplicação requer um driver que suporte OpenGL 3.3.

## Início rápido no Linux

No terminal, a partir da raiz do projeto:

```bash
chmod +x instalar_linux.sh executar_linux.sh benchmark_linux.sh
./instalar_linux.sh
./executar_linux.sh
```

Em Debian/Ubuntu, caso o GLFW indique bibliotecas de sistema ausentes:

```bash
sudo apt install libgl1-mesa-dri libglfw3 libxrandr2 libxinerama1 libxcursor1 libxi6
```

## Controles

| Entrada | Ação |
| --- | --- |
| `W`, `A`, `S`, `D` | Mover a câmera |
| `Q` / `E` | Descer / subir |
| Botão direito + mouse | Olhar ao redor |
| Roda do mouse | Ajustar a velocidade |
| `L` | Alternar entre COM LOD e SEM LOD |
| `F` | Alternar entre preenchimento e wireframe |
| `T` | Ligar ou desligar a camada de temperatura média |
| `+` / `-` | Ajustar a opacidade em 5 pontos percentuais, de 0% a 100%. No teclado principal, `=` também aumenta a opacidade |
| `R` | Restaurar a câmera |
| `B` | Iniciar ou encerrar a gravação manual de métricas |
| `F12` | Salvar captura PNG em `outputs` |
| `Esc` | Sair |

A textura aparece desde o início. A camada de temperatura começa desligada e usa 50% de opacidade quando ligada pela primeira vez. O título da janela mostra o modo LOD, os FPS, a quantidade de triângulos, a distribuição dos patches e o estado da camada térmica.

## Experimento para o artigo

Execute `benchmark_windows.bat` no Windows, `./benchmark_linux.sh` no Linux ou, com o ambiente virtual ativo:

```bash
python main.py --benchmark --seconds 12 --no-vsync
```

Cada modo faz dois segundos de aquecimento e doze segundos de medição. A câmera segue a mesma trajetória em função do tempo, com VSync desativado. O número de quadros e seus instantes de amostragem podem diferir entre os modos. Os resultados ficam em `outputs`:

- `benchmark_opengl_comparacao_frames.csv` — tempo por quadro, FPS, triângulos, posição da câmera e distribuição dos patches.
- `benchmark_opengl_comparacao_resumo.csv` — médias por modo, desvio-padrão e percentil 95 do tempo por quadro, além das contagens de triângulos.
- `benchmark_opengl_comparacao_grafico.png` — gráficos comparativos de FPS, tempo por quadro e triângulos.

Para repetir o experimento, mantenha a resolução e as configurações da cena, feche programas pesados e faça mais de uma rodada. Guarde os resultados de cada rodada, pois o benchmark reutiliza os nomes dos arquivos. Registre CPU, GPU, memória, sistema operacional, resolução e versão do Python. Use o tempo por quadro para avaliar se a redução de triângulos se traduziu em ganho de desempenho.

## Dados usados no projeto

| Arquivo em `data/` | Fonte e função |
| --- | --- |
| `S23W048.tif` | GeoTIFF de elevação **SRTM GL1**, obtido no [Global DEM Portal](https://globaldemportal.github.io/). A cópia local coincide pelo SHA-256 com o [bloco distribuído pelo OpenTopography](https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/S23W048.tif). Define as alturas da malha. |
| `fd66efe1267676ede44532d9b6397cc3.grib` | Temperatura do ar a 2 m do [ERA5-Land](https://doi.org/10.24381/cds.e2161bac), versão preliminar ERA5-Land-T. Contém 288 campos horários, de 01/11/2026 às 00:00 a 12/11/2026 às 23:00 UTC. |
| `2026-10-27-00_00_2026-10-27-23_59_Sentinel-2_L2A_True_color.jpg` | Imagem **Sentinel-2 L2A True Color**, exportada do [Copernicus Browser](https://browser.dataspace.copernicus.eu/) para 27/10/2026. Fornece a textura de fundo. |

O recorte do DEM vai de 23° S a 22° S e de 48° O a 47° O. A aplicação converte as temperaturas de kelvin para Celsius, calcula a média dos 288 horários em cada ponto da grade de 11 × 11 e interpola o campo médio para o terreno. Com esses arquivos, as temperaturas médias exibidas vão de **21,43 a 23,22 °C**. A interpolação preenche a visualização entre pontos da grade original, cuja resolução meteorológica permanece de 0,1°.

O JPG não inclui coordenadas. A configuração assume norte no topo e o mesmo recorte do DEM. A imagem de outubro fornece contexto visual para a temperatura média de novembro.

Na primeira execução, o programa gera `data/meteorologia_real.npz` a partir do TIFF e do GRIB. Alterações nas fontes ou no tamanho da grade invalidam esse cache. O JPG é lido separadamente. Para preparar os dados sem abrir a janela:

```bash
python main.py --prepare-data
```

## Dados próprios

Para trabalhar diretamente com outro par de dados georreferenciados, mantenha `terrain.source` como `georeferenced` e ajuste `terrain.heightmap` e `terrain.temperature_file`. Se usar uma nova textura, atualize o caminho e os limites. O importador espera um DEM orientado ao norte e um GRIB de temperatura do ar a 2 m com cobertura para o recorte.

Também é possível gerar um NPZ separado. Com o ambiente virtual ativo:

```bash
python tools/import_dataset.py --height caminho/relevo.tif --temperature caminho/temperatura.grib --output data/meteorologia_importada.npz
```

O importador também aceita imagens reconhecidas pelo Pillow, `.npy`, `.csv` e `.txt`. Com alturas e temperaturas em matrizes sem georreferenciamento, as grades precisam representar o mesmo recorte e a mesma orientação. Por exemplo:

```bash
python tools/import_dataset.py --height caminho/relevo.png --temperature caminho/temperatura.csv --output data/meteorologia_importada.npz
```

Os formatos numéricos de temperatura são interpretados em Celsius. Para importar apenas a elevação, omita `--temperature`. Nesse caso, a ferramenta gera temperaturas demonstrativas a partir da altura. O tamanho padrão do importador é 513 × 513 e pode ser ajustado com `--size`.

Para abrir o arquivo importado, use `terrain.source` igual a `npz` e aponte `terrain.dataset` para o NPZ. Se o NPZ não tiver georreferenciamento ou corresponder a outro recorte, retire a textura e os limites do recorte original ou configure uma imagem compatível. O NPZ contém duas matrizes quadradas `float32`, `elevation` normalizada de 0 a 1 e `temperature` em Celsius, além de `metadata` com os metadados disponíveis. Para uma cena de demonstração totalmente sintética, use `terrain.source` igual a `synthetic`, um caminho NPZ separado e retire a textura geográfica.

## Configuração

As principais opções estão em `config.json`.

| Campo | Função | Padrão |
| --- | --- | --- |
| `terrain.source` | Entrada georreferenciada, NPZ ou geração sintética | `georeferenced` |
| `terrain.dataset` | Caminho do cache ou do NPZ de entrada | `data/meteorologia_real.npz` |
| `terrain.heightmap` / `terrain.temperature_file` | Arquivos de elevação e temperatura | GeoTIFF SRTM e GRIB ERA5-Land |
| `terrain.texture` / `terrain.texture_bounds_wgs84` | Imagem e limites oeste, sul, leste e norte | Sentinel-2 e `[-48, -23, -47, -22]` |
| `terrain.grid_size` | Amostras da malha por lado | 513 |
| `terrain.world_size` | Largura em unidades da cena. A profundidade acompanha a proporção do recorte geográfico | 512 |
| `terrain.vertical_scale` | Escala visual da elevação normalizada | 58 |
| `terrain.patch_size` | Células por lado de cada patch | 32 |
| `terrain.lod_strides` | Passos de amostragem dos níveis | `[1, 2, 4, 8]` |
| `terrain.lod_distances` | Distâncias de troca de nível | `[150, 280, 430]` |
| `terrain.skirt_depth` | Profundidade das saias nas bordas | 8 |
| `rendering.temperature_auto_range` | Ajusta a paleta à faixa do campo importado | `true` |
| `rendering.temperature_min` / `rendering.temperature_max` | Limites em °C quando a faixa automática está desligada | 8 / 36 |
| `rendering.temperature_overlay` / `rendering.temperature_opacity_percent` | Visibilidade e opacidade iniciais da camada | `false` / 50 |

Para a malha, `grid_size - 1` deve ser múltiplo de `patch_size` e cada passo de LOD deve dividir `patch_size`. A textura precisa cobrir o terreno. O mapeamento pelos limites WGS84 pressupõe uma grade de latitude e longitude sem rotação.

## Estrutura do projeto

```text
.
├── main.py                  # Inicialização e argumentos de linha de comando
├── config.json              # Parâmetros da cena e do experimento
├── requirements.txt         # Dependências Python
├── shaders/                 # Vertex shader e fragment shader em GLSL
├── src/
│   ├── application.py       # Janela, eventos e loop de renderização
│   ├── camera.py            # Câmera 3D livre
│   ├── math3d.py            # Matrizes de visão e projeção
│   ├── dataset.py           # Formato NPZ e dados de demonstração
│   ├── geodata.py           # Importação georreferenciada e média térmica
│   ├── terrain_cpu.py       # Malha, normais, saias e seleção de LOD
│   ├── terrain_gl.py        # Buffers, textura e desenho OpenGL
│   ├── shader.py            # Compilação e parâmetros dos shaders
│   ├── metrics.py           # Medição e exportação em CSV
│   └── charts.py            # Gráficos do experimento
├── tools/                   # Geração, importação e gráficos
├── tests/                   # Testes independentes da GPU
├── data/                    # Arquivos de entrada e cache
└── outputs/                 # CSV, gráficos e capturas
```
