# Prévias Tekó Biotech V2

Entrega 1: duas direções visuais navegáveis, com dados inteiramente fictícios. Não há chamadas de API, acesso a banco, cadastro de sensores ou envio de mensagens.

Abra [`index.html`](index.html) diretamente no navegador. Não é necessário instalar dependências. Os arquivos de estilo, script e marca estão na mesma pasta e funcionam sem internet. JavaScript precisa estar habilitado.

Para servir apenas a prévia pelo notebook, a partir da raiz do projeto:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory prototipo-v2
```

Abra `http://127.0.0.1:4173`. Encerre com `Ctrl+C`.

Para conferir no celular da mesma rede, substitua `127.0.0.1` por `0.0.0.0` no comando e abra `http://IP-DO-NOTEBOOK:4173`. O comando serve somente `prototipo-v2/`; não sirva a raiz do repositório. Acesso LAN depende do roteador e do firewall e ainda exige ensaio físico.

## Roteiro de revisão

1. No topo, compare **A · Campo** e **B · Observatório**. Campo abre por padrão apenas como proposta inicial, sem decisão aprovada.
2. Em Início, encontre a Estufa 01 e confira origem, horário e idade da leitura.
3. Abra o ponto; troque parâmetro e período, consulte a tabela e exporte um CSV fictício. O booleano falso é um resultado válido, mostrado como “Não detectada”.
4. Abra a ocorrência, leia regra, início e situação do Telegram. Em Alertas, filtre também as encerradas.
5. No seletor **Cenário**, revise primeira instalação, primeira leitura, carregamento, API offline com/sem consulta guardada, sensor offline, leitura antiga, erro, calibração, substituição, horário desconhecido e histórico vazio.
6. Abra Preparação para percorrer a primeira conexão e as responsabilidades administrativas no notebook.
7. Compare as larguras 360, 390, 768 e 1366 px e navegue com Tab/Shift+Tab/Enter. O menu fica na parte inferior em telas menores.

O relógio é fixo em **16/11/2026, 10:42, UTC−3**. As idades não avançam com o relógio do computador. O cenário “com última consulta” representa visualmente um cache, mas não implementa armazenamento offline. Botões “Simular…” apenas trocam o cenário local. Não há detecção real de conexão.

Rotas usam fragmentos (`#inicio`, `#ponto/estufa`, `#alerta/estufa`), permitindo abrir/recarregar diretamente sem configurar servidor. Direção e cenário são refletidos na query quando o navegador permite, por exemplo:

```text
index.html?direction=observatorio&scenario=api-cache#ponto/estufa
```

## Arquivos

| Arquivo | Objetivo |
| --- | --- |
| `index.html` | Estrutura acessível, controles da revisão e navegação. |
| `styles.css` | Duas direções visuais, componentes, estados e layouts responsivos. |
| `app.js` | Fixtures, navegação, cenários, histórico e exportação demonstrativa. |
| `marca.svg` | Símbolo vetorial provisório para a prévia; não é uma redefinição aprovada da marca. |

Veja o [relatório da entrega](../docs/ENTREGA-1-PREVIAS-V2.md) e a [decisão de tecnologia](../docs/decisoes/001-previa-interface-v2.md). Os frontends em `frontend/` e `web/` permanecem referências da integração posterior.
