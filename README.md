# Visualizacao Meteorologica Multirresolucao

Gabriel Marques Paulon RA: 113142 
Gustavo Tesche RA: 113265

Aplicacao desktop em **Python + OpenGL 3.3** para visualizar um campo de
temperatura sobre um terreno construído a partir de heightmap. O mesmo cenario
pode ser renderizado com uma malha uniforme ou com selecao automatica de niveis
de detalhe (LOD), permitindo uma comparacao experimental direta.

## O que esta implementado

- camera 3D livre com perspectiva;
- terreno procedural `257 x 257` com elevacao e temperatura;
- divisao do terreno em `8 x 8 = 64` patches;
- quatro resolucoes por patch, com strides `1`, `2`, `4` e `8`;
- escolha automatica do LOD pela distancia horizontal ate a camera;
- skirts nas bordas dos patches para esconder frestas entre resolucoes;
- versoes **SEM LOD** e **COM LOD** na mesma aplicacao;
- mapa de cores de temperatura e iluminacao GLSL;
- contador de FPS, tempo por quadro, triangulos e patches por nivel;
- benchmark automatico com a mesma trajetoria de camera nos dois modos;
- exportacao de quadros e resumo em CSV;
- grafico PNG comparando FPS, tempo de quadro e triangulos;
- captura de tela e importacao de heightmaps externos.

## Inicio rapido no Windows

1. Instale o [Python 3.12](https://www.python.org/downloads/) e marque
   **Add Python to PATH** durante a instalacao.
2. Abra esta pasta e execute `instalar_windows.bat` uma unica vez.
3. Execute `executar_windows.bat` para abrir a visualizacao.
4. Execute `benchmark_windows.bat` para gerar a comparacao experimental.

O instalador cria um ambiente virtual local em `.venv` e instala as versoes
compativeis de NumPy, GLFW, PyOpenGL, Pillow e Matplotlib. Nao e necessario
instalar essas bibliotecas manualmente.

## Inicio rapido no Linux

No terminal, dentro desta pasta:

```bash
chmod +x instalar_linux.sh executar_linux.sh benchmark_linux.sh
./instalar_linux.sh
./executar_linux.sh
```

Em distribuicoes Debian/Ubuntu, se o GLFW reclamar de bibliotecas do sistema:

```bash
sudo apt install libgl1-mesa-dri libglfw3 libxrandr2 libxinerama1 libxcursor1 libxi6
```

## Controles

| Entrada | Acao |
|---|---|
| `W`, `A`, `S`, `D` | mover a camera |
| `Q` / `E` | descer / subir |
| botao direito + mouse | olhar ao redor |
| roda do mouse | alterar velocidade |
| `L` | alternar entre COM LOD e SEM LOD |
| `F` | alternar preenchimento e wireframe |
| `R` | restaurar a camera |
| `B` | iniciar/finalizar gravacao manual em CSV |
| `F12` | salvar captura PNG em `outputs` |
| `Esc` | sair |

A barra de titulo mostra o modo atual, FPS, quantidade de triangulos e a
distribuicao dos patches nos quatro niveis.

## Experimento para o artigo

Execute `benchmark_windows.bat` ou:

```bash
python main.py --benchmark --seconds 12 --no-vsync
```

Cada modo recebe dois segundos de aquecimento e doze segundos de medicao. A
camera percorre exatamente a mesma trajetoria nas duas fases. Ao final, a pasta
`outputs` recebe:

- `*_frames.csv`: uma linha por quadro;
- `*_resumo.csv`: medias, desvio-padrao, percentil 95 e triangulos;
- `*_grafico.png`: tres graficos prontos para analisar e inserir no artigo.

Para uma comparacao correta, feche programas pesados, use a mesma resolucao de
janela e execute o benchmark mais de uma vez. Informe no artigo CPU, GPU,
memoria, sistema operacional, resolucao e versao do Python usados.

## Dados proprios

O programa cria `data/meteorologia_sintetica.npz` automaticamente. Para usar um
heightmap real, ative o ambiente virtual e execute:

```bash
python tools/import_dataset.py --height caminho/heightmap.png
```

Tambem e possivel fornecer temperatura:

```bash
python tools/import_dataset.py \
  --height caminho/relevo.tif \
  --temperature caminho/temperatura.csv \
  --output data/meteorologia_importada.npz
```

Formatos aceitos: imagens reconhecidas pelo Pillow, `.npy`, `.csv` e `.txt`.
Depois, altere `terrain.dataset` em `config.json` para o novo NPZ. A grade e
redimensionada para `257 x 257` por padrao, tamanho compativel com os patches.

O NPZ final contem:

- `elevation`: matriz quadrada `float32`, normalizada entre 0 e 1;
- `temperature`: matriz quadrada `float32`, em graus Celsius.

## Configuracao

As principais opcoes estao em `config.json`:

| Campo | Funcao |
|---|---|
| `grid_size` | quantidade de amostras por lado |
| `world_size` | largura/profundidade do terreno |
| `vertical_scale` | exagero vertical do heightmap |
| `patch_size` | celulas por lado de cada patch |
| `lod_strides` | passo de amostragem de cada nivel |
| `lod_distances` | distancias de troca entre niveis |
| `skirt_depth` | profundidade das saias anti-fresta |
| `temperature_min/max` | limites do mapa de cores |

Para esta implementacao, `grid_size - 1` deve ser divisivel por `patch_size`, e
cada valor de `lod_strides` deve dividir `patch_size`.

## Estrutura do projeto

```text
Projeto_Meteorologia_OpenGL/
|-- main.py                  ponto de entrada
|-- config.json              parametros do experimento
|-- requirements.txt         bibliotecas Python
|-- shaders/                 vertex e fragment shaders GLSL
|-- src/
|   |-- application.py       janela, eventos e loop de renderizacao
|   |-- camera.py            camera 3D livre
|   |-- dataset.py           dados sinteticos e formato NPZ
|   |-- terrain_cpu.py       patches, malha, normals, skirts e LOD
|   |-- terrain_gl.py        buffers e desenho OpenGL
|   |-- metrics.py           FPS e CSV
|   `-- charts.py            grafico do experimento
|-- tools/                   geracao, importacao e graficos
|-- tests/                   testes independentes da GPU
|-- data/                    conjuntos de dados
`-- outputs/                 CSV, graficos e capturas
```

## Testes

Com o ambiente virtual ativo:

```bash
python -m unittest discover -s tests -v
```

Os testes verificam geracao e persistencia dos dados, calculo das normais,
quantidade de patches e triangulos, reducao geometrica entre LODs e matrizes da
camera.

## Solucao de problemas

- **Python nao encontrado:** reinstale o Python marcando `Add Python to PATH`.
- **Janela OpenGL nao abre:** atualize o driver da GPU. E necessario OpenGL 3.3.
- **Tela preta:** restaure a camera com `R` e confira os shaders no terminal.
- **FPS limitado a 60:** o modo normal usa VSync; o benchmark o desativa.
- **Notebook com duas GPUs:** selecione a GPU de alto desempenho para o Python
  nas configuracoes graficas do sistema.

## Creditos tecnicos

Projeto academico baseado em heightmaps, particionamento espacial em patches e
niveis de detalhe discretos. A implementacao usa somente Python, NumPy,
GLFW/PyOpenGL, GLSL, Pillow e Matplotlib.
