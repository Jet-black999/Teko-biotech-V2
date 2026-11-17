# Decisão 001 — tecnologia da prévia V2

Data: 16/11/2026. Estado: **adotada para a prévia; tecnologia do dashboard integrado ainda proposta**.

## Contexto

A entrega 1 precisa permitir comparar direções e jornadas antes de construir as demais telas. Existem bloqueios de instalação registrados na entrega 0. O frontend anterior não é requisito visual e nenhuma dependência deve ser atualizada por tentativa para viabilizar esta revisão.

## Comparação

| Opção | Manutenção | Dependências | Reaproveitamento de lógica | Integração posterior |
| --- | --- | --- | --- | --- |
| HTML/CSS/JS isolados | Simples para a prévia; renderização manual perde vantagem conforme o painel cresce | Nenhuma instalação, fonte ou CDN | Conceitos e estados reaproveitados; sem importar componentes antigos | Exige separar componentes e adaptar estado/cliente se adotarmos React depois |
| React/TypeScript/Vite existente | Tipos e componentes favorecem o dashboard integrado | React, React DOM, Vite, TypeScript e build; instalação limpa ainda não validada | Maior reaproveitamento potencial de `frontend/src/domain/model.ts`, `data/api.ts` e testes | Pode receber o novo visual sem preservar o layout antigo; requer revisão dos contratos e do tratamento de estados |
| Introduzir outro framework | Nova convenção e aprendizado para manter | Novo conjunto de pacotes e build | Menor reaproveitamento direto dos componentes React | Custo adicional sem necessidade demonstrada nesta entrega |

## Decisão

Criar `prototipo-v2/` com HTML/CSS/JS e SVG locais. Abrir por arquivo ou servidor estático, sem tocar em manifests, locks, API ou dados existentes. As duas direções usam os mesmos dados e navegação; a diferença inclui hierarquia, tipografia, cores e apresentação de pontos em cartões ou lista comparativa no desktop.

Para o dashboard integrado, **propor React/TypeScript/Vite** pelo código de domínio/cliente já disponível, sujeito à revisão visual e à resolução da instalação reproduzível. Esta proposta não obriga preservar o frontend antigo nem autoriza migrá-lo nesta entrega. A escolha definitiva será registrada antes da integração da entrega 3.

## Consequências e limites

- A prévia é código descartável para validação de experiência, não um segundo dashboard operacional.
- Layout, tokens e redação podem ser portados; fixtures, valores e regras experimentais não entram no modo físico.
- Estados de comunicação devem vir do contrato real. A troca manual de cenário não valida cache, reconexão, heartbeat, idade ou qualidade em produção.
- O cliente existente não foi copiado cegamente: sua normalização, origem, aquisição e tratamento de dados inválidos serão revisados com a API consolidada.
- Tipos numérico/categórico/booleano e distinção entre aquisição/recebimento se baseiam nos contratos consultados, mas a prévia não certifica compatibilidade com a API.
- Nenhum framework novo, pacote externo, serviço de fontes, hospedagem ou publicação foi introduzido.
