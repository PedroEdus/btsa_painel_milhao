# CONTEXT.md — Painel da Campanha do Milhão

## 1. Finalidade deste documento

Este documento consolida o contexto necessário para desenvolver a primeira entrega do **Painel da Campanha do Milhão**, com foco principal na atuação de **Pedro, Especialista em Analytics**, responsável pela construção do MVP visual e pela integração da aplicação com a base disponibilizada pelo time de dados.

O conteúdo foi sintetizado a partir de três reuniões:

1. introdução do projeto ao time de dados;
2. alinhamento das configurações finais da campanha;
3. definição do plano de ação para a primeira entrega.

Este arquivo não reproduz transcrições brutas, consultas SQL completas ou o dicionário de dados do UAU. Esses materiais devem permanecer como fontes técnicas de consulta e não como parte do contexto operacional do MVP.

---

# 2. Visão geral do projeto

## 2.1 O que é a Campanha do Milhão

A Campanha do Milhão é uma ação promocional da Brasil Terrenos para incentivar entrada de caixa, regularização financeira, adiantamento de parcelas, permanência da adimplência e relacionamento com a base de clientes.

A campanha está prevista para acontecer no segundo semestre, com início em **1º de julho** e movimentações consideradas até dezembro. A estrutura apresentada nas reuniões contempla:

- cinco sorteios mensais de casas mobiliadas com carro na garagem;
- um prêmio final de R$ 1 milhão em barras de ouro;
- sorteios mensais realizados no mês subsequente ao período de geração dos cupons;
- sorteio final do prêmio de R$ 1 milhão após o encerramento do período da campanha.

O primeiro sorteio mensal deverá considerar os pagamentos de julho e ocorrer em agosto. A mesma lógica deverá se repetir nos meses seguintes.

## 2.2 Objetivo estratégico

O objetivo central não é apenas promover sorteios. A campanha busca aumentar a arrecadação da empresa por meio de:

- pagamento regular de parcelas;
- recuperação de clientes inadimplentes;
- liquidação de valores em atraso;
- antecipação de parcelas futuras;
- estímulo à permanência da adimplência;
- aumento do caixa realizado durante o período da campanha.

O painel deve mostrar se a campanha está produzindo esse efeito financeiro. Portanto, ele não deve se limitar a contar cupons. Deve permitir acompanhar participação, pagamentos, recuperação financeira e evolução da carteira.

---

# 3. Papel do time de dados

O time de dados foi responsabilizado por duas entregas principais:

1. construir a base que identifica os pagamentos elegíveis e calcula a quantidade de cupons;
2. desenvolver um painel para acompanhamento gerencial da campanha.

O time de dados não será o emissor oficial dos cupons. A geração e a disponibilização dos números oficiais deverão ser realizadas por uma empresa ou plataforma terceira.

A base interna deverá funcionar como fonte de cálculo, validação e conferência. A quantidade calculada internamente precisa ser reconciliável com a quantidade efetivamente gerada pela plataforma externa.

Isso cria duas noções diferentes que não podem ser confundidas:

- **cupons calculados:** quantidade obtida a partir das regras aplicadas aos recebimentos do UAU;
- **cupons oficiais:** números efetivamente emitidos e vinculados ao cliente pela plataforma da campanha.

Na primeira entrega, o painel poderá trabalhar principalmente com os cupons calculados. Uma consulta aos números oficiais dependerá de integração ou retorno da plataforma externa.

---

# 4. Participantes e responsabilidades

## 4.1 Pedro — Especialista em Analytics

Pedro será o responsável principal pela construção do **MVP do painel**, com foco em aplicação, experiência visual, indicadores e integração com a fonte de dados preparada pelo time.

Responsabilidades diretas:

- estruturar o projeto da aplicação;
- desenvolver o MVP inicialmente em Streamlit;
- conectar o painel à estrutura disponibilizada no Microsoft Fabric;
- criar cards, gráficos, filtros e visões executivas;
- aplicar a identidade visual da campanha;
- buscar com o Marketing os materiais visuais oficiais;
- testar atualização automática e comportamento de cache;
- avaliar o uso controlado de HTML, CSS e componentes JavaScript;
- garantir que o painel seja responsivo e utilizável em telas e dispositivos móveis;
- apresentar uma primeira versão funcional ao time;
- ajustar o MVP com base na validação de Carlos e dos responsáveis pelo negócio;
- explicitar no painel quando um dado é calculado internamente e quando é oficial da plataforma externa.

Pedro não é o responsável por descobrir sozinho as regras do UAU nem por aprovar regras de negócio. A implementação deve utilizar regras validadas por Carlos e pelas áreas responsáveis pela campanha.

## 4.2 Carlos — Head da área de dados

Carlos é o responsável por coordenar a entrega, traduzir as regras para a base e finalizar a consulta usada pelo MVP.

Responsabilidades principais:

- concluir a consulta SQL;
- identificar e relacionar as tabelas corretas do UAU;
- aplicar as regras de recebimento e elegibilidade;
- consolidar os dados em uma granularidade adequada;
- validar valores e quantidade de cupons;
- explicar as regras do UAU ao restante do time;
- apoiar Pedro durante a construção do painel;
- validar se os indicadores representam corretamente a base;
- conduzir a validação com o negócio.

## 4.3 Vinicius — Engenharia de Dados / Microsoft Fabric

Vinicius será o principal apoio na frente de dados dentro do Microsoft Fabric.

Responsabilidades principais:

- identificar as tabelas necessárias para a consulta;
- disponibilizar as estruturas no Fabric;
- criar ou apoiar a criação da visão ou tabela consolidada;
- apoiar autenticação e conexão da aplicação;
- avaliar workspace, permissões e organização do ambiente;
- colaborar com a evolução futura da arquitetura;
- apoiar Pedro na solução de limitações técnicas de integração e publicação.

## 4.4 Marketing, Comercial, Jurídico e TI

As demais áreas possuem papéis complementares:

- **Marketing:** comunicação, identidade visual, materiais da campanha e condução operacional da divulgação;
- **Comercial/Diretoria:** decisões sobre mecânica, orçamento, prêmios e regras comerciais;
- **Jurídico:** validação do regulamento, titularidade, consentimento, LGPD e entrega dos prêmios;
- **TI:** acessos e integrações necessárias, principalmente serviços e APIs disponibilizados à plataforma externa;
- **empresa terceira:** geração e gestão oficial dos cupons e experiência do cliente no hotsite ou plataforma da campanha.

---

# 5. Regras de negócio consolidadas

## 5.1 Regra básica de geração

A regra discutida e posteriormente esclarecida é baseada no **valor pago**, e não na quantidade de parcelas.

Referência definida nas reuniões:

- a cada R$ 100 considerados, o cliente gera um cupom;
- o cálculo é realizado sobre o valor recebido durante o período aplicável;
- o agrupamento operacional deve respeitar empresa, obra e venda;
- o CPF identifica o cliente, mas a origem financeira continua vinculada à venda.

A fórmula exata de arredondamento precisa ser registrada no código e validada. A hipótese mais coerente é utilizar somente blocos completos de R$ 100, mas isso não deve ser assumido silenciosamente.

Exemplo:

- R$ 1.000 elegíveis geram 10 cupons;
- R$ 244 exigem confirmação sobre gerar 2 cupons e manter ou descartar o saldo de R$ 44;
- valores de vendas diferentes não devem ser somados automaticamente sem confirmar a regra de agrupamento.

## 5.2 Pagamentos elegíveis

A lógica geral discutida foi considerar o dinheiro efetivamente recebido pela empresa, incluindo diferentes comportamentos do cliente:

- parcelas regulares pagas no mês;
- parcelas vencidas regularizadas;
- pagamentos decorrentes de negociação ou renegociação;
- antecipação de parcelas futuras;
- quitação de valores em atraso;
- outros tipos de parcelas aprovados pelo regulamento.

A classificação dos tipos de parcela deve permanecer disponível na base para auditoria, mesmo quando diferentes categorias gerarem cupom da mesma forma.

## 5.3 Multa, juros e custas

Este ponto apresentou divergências entre reuniões e precisa ser tratado com cautela.

Na introdução técnica, foi discutida a utilização apenas do valor principal, sem multa e juros. No alinhamento final, surgiu a orientação de que o foco é o dinheiro que entrou e que apenas custas deveriam ser excluídas, permitindo que juros e multas gerassem cupons.

Para o desenvolvimento, a regra não pode permanecer implícita. O código deve parametrizar separadamente:

- valor principal;
- multa;
- juros;
- custas;
- valor total considerado para cupom.

Até a validação formal do regulamento, o painel deve permitir conferir esses componentes sem consolidá-los de maneira irreversível.

## 5.4 Sorteios mensais

Os cupons usados em cada sorteio de casa são referentes ao período mensal correspondente.

Exemplo:

- pagamentos de julho geram cupons para o sorteio realizado em agosto;
- ao iniciar o mês seguinte, inicia-se uma nova apuração para a próxima casa;
- os cupons mensais não permanecem concorrendo às casas dos meses seguintes.

## 5.5 Prêmio final de R$ 1 milhão

Para o prêmio final, os cupons gerados ao longo da campanha são acumulados.

Um cliente que gerou cupons em vários meses deverá manter esse acumulado para o sorteio final, sujeito às regras de cadastro, aceite e elegibilidade.

O ganhador de uma casa deixa de participar dos sorteios mensais seguintes, mas continua elegível ao prêmio final de R$ 1 milhão, conforme a regra discutida.

## 5.6 Inadimplência e regularização

A campanha foi desenhada também para estimular a recuperação de inadimplentes.

O pagamento de valores atrasados pode gerar cupons no mês em que o dinheiro efetivamente entra. Entretanto, houve preocupação de que um cliente pudesse concentrar vários pagamentos atrasados em um único mês e obter grande quantidade de cupons para uma casa.

Esse risco foi discutido, mas a regra definitiva deve ser confirmada no regulamento. O painel deve manter informação suficiente para distinguir:

- pagamento regular;
- pagamento de parcela vencida;
- cliente inadimplente antes do pagamento;
- cliente adimplente após regularização;
- valor recuperado da inadimplência;
- quantidade de cupons gerada por regularização.

## 5.7 Cadastro e aceite

A participação depende de cadastro ou aceite do cliente na plataforma da campanha.

Pontos discutidos:

- o cadastro representa o aceite do cliente;
- após cadastrado, o cliente permanece participante nos meses seguintes;
- existe impacto de LGPD na disponibilização dos dados;
- houve dúvida sobre considerar pagamentos anteriores ao cadastro;
- a regra sobre retroatividade ainda precisa de confirmação formal.

A base e o painel devem manter separadas as seguintes informações:

- cliente gerou valor elegível;
- cliente gerou cupons calculados;
- cliente realizou cadastro/aceite;
- cupons estão habilitados para participação;
- cupons foram emitidos oficialmente.

## 5.8 Venda com mais de um comprador

Foi discutido que uma venda pode possuir mais de um adquirente, mas existe um titular principal operacionalmente utilizado para cobrança e comunicação.

A tendência definida foi:

- a venda gera uma única quantidade de cupons;
- os cupons não devem ser duplicados como novas chances para cada sócio;
- a participação e a entrega do prêmio devem estar ligadas ao titular principal;
- os demais compradores precisam ser tratados conforme o regulamento e o fluxo da plataforma;
- o Jurídico deve validar autorização, ciência e divisão do direito ao prêmio.

No modelo de dados, é necessário evitar duplicação de valor e de cupons quando uma venda possui múltiplos compradores.

---

# 6. Dados necessários para o MVP

A consulta consolidada deverá fornecer, no mínimo, informações suficientes para as dimensões e métricas abaixo.

## 6.1 Identificação da venda e do cliente

- empresa;
- obra;
- cidade;
- produto ou empreendimento;
- número da venda;
- identificação da unidade ou lote, quando necessária;
- CPF do titular;
- nome do cliente;
- telefone;
- e-mail, quando disponível;
- indicação de titularidade;
- quantidade de compradores vinculados à venda.

## 6.2 Informações financeiras

- data do recebimento;
- competência ou mês da campanha;
- valor principal;
- multa;
- juros;
- custas;
- valor total recebido;
- valor considerado para geração de cupons;
- tipo da parcela;
- origem do pagamento;
- indicação de antecipação;
- indicação de negociação ou renegociação;
- indicação de pagamento vencido;
- quantidade de parcelas pagas.

## 6.3 Elegibilidade e cupons

- status de cadastro ou aceite;
- status de elegibilidade;
- motivo de bloqueio;
- quantidade de cupons calculados no mês;
- quantidade acumulada para o milhão;
- quantidade oficial emitida, quando disponível;
- diferença entre calculado e oficial;
- indicador de cliente já contemplado com casa;
- participação permitida nos próximos sorteios;
- data da última atualização.

## 6.4 Inadimplência

- status anterior ao pagamento;
- dias de atraso;
- quantidade de parcelas vencidas;
- valor vencido antes da regularização;
- valor recuperado;
- status depois do pagamento;
- classificação entre recebimento normal e recuperação.

---

# 7. Granularidade e modelagem para consumo

Carlos indicou que a consulta final deverá ser consolidada principalmente no nível de venda, evitando entregar ao painel uma linha por parcela.

A primeira entrega pode utilizar uma tabela de consumo sumarizada, desde que preserve as chaves necessárias para auditoria.

Granularidade sugerida para o MVP:

- empresa;
- obra;
- venda;
- CPF titular;
- mês de referência;
- tipo de recebimento ou classificação principal.

Medidas agregadas:

- valor total recebido;
- valor elegível;
- quantidade de parcelas;
- quantidade de cupons;
- valor recuperado;
- situação de elegibilidade.

Mesmo que o painel leia uma estrutura consolidada, deve existir uma forma de rastrear os dados até os recebimentos de origem. Sem essa rastreabilidade, divergências com clientes ou com a plataforma externa serão difíceis de investigar.

---

# 8. Arquitetura da primeira entrega

## 8.1 Diretriz principal

A aplicação não deve se conectar diretamente ao banco operacional do UAU.

A arquitetura acordada como direção para o MVP é:

```text
UAU / banco de origem
        ↓
Consulta e consolidação desenvolvida por Carlos
        ↓
Microsoft Fabric
        ↓
View ou tabela de consumo
        ↓
Aplicação Streamlit desenvolvida por Pedro
```

## 8.2 Microsoft Fabric

O Fabric será utilizado como camada intermediária por questões de:

- segurança;
- isolamento do banco operacional;
- capacidade de processamento;
- facilidade de atualização;
- possibilidade de evolução posterior;
- integração com o ambiente de dados da empresa.

A primeira entrega não deverá tentar implantar toda a arquitetura medalhão. O prazo é curto e a prioridade é disponibilizar uma fonte funcional e validada.

Abordagem temporária aceita:

- carregar apenas as tabelas essenciais;
- reproduzir ou materializar a lógica da consulta;
- gerar uma única tabela ou view de consumo;
- refatorar depois da entrega inicial.

## 8.3 Streamlit

O Streamlit foi escolhido para o MVP por permitir desenvolvimento rápido com Python e integração direta com bibliotecas de dados.

Vantagens para a entrega:

- Pedro já possui experiência com a ferramenta;
- construção rápida de aplicação web;
- integração com Pandas e fontes SQL;
- suporte a componentes HTML e CSS;
- possibilidade de inserir componentes JavaScript quando necessário;
- responsividade;
- facilidade para criar e testar o MVP;
- menor curva de aprendizado do que iniciar uma aplicação JavaScript completa.

O MVP poderá ser substituído futuramente por uma aplicação web mais robusta. Essa migração não será automática: regras, dados e conceitos poderão ser reaproveitados, mas a interface provavelmente precisará ser reconstruída.

## 8.4 Hospedagem

A aplicação deverá preferencialmente ser hospedada em ambiente controlado pela empresa.

Possibilidades discutidas:

- servidor interno;
- container Docker;
- ambiente de aplicação conectado ao Fabric;
- Streamlit privado apenas como alternativa de validação.

O uso do Streamlit Community Cloud não deve ser assumido como ambiente definitivo, devido a segurança, controle de acesso e sensibilidade dos dados.

---

# 9. Atualização dos dados

O termo “tempo real” foi usado nas reuniões, mas a solução discutida é tecnicamente **near real-time**.

A expectativa é que pagamentos recentes apareçam no painel após poucos minutos.

Frequências consideradas:

- a cada cinco minutos;
- a cada dez minutos;
- frequência maior no horário comercial;
- frequência reduzida fora do horário comercial.

A decisão deve considerar:

- tempo real da consulta completa;
- consumo do Fabric;
- comportamento do cache do Streamlit;
- quantidade de usuários;
- estabilidade da conexão;
- necessidade de acesso fora do horário comercial.

Como a consulta consolidada foi relatada com execução próxima de quatro segundos, o time considerou viável testar refresh a cada cinco minutos. Esse número precisa ser reavaliado com a versão completa da consulta e com concorrência real.

No Streamlit, a atualização deve ser controlada por TTL de cache ou mecanismo equivalente. Apenas recarregar a página não garante uma nova consulta à base.

---

# 10. Escopo visual do MVP

## 10.1 Princípios

O painel deve ser:

- executivo;
- visualmente impactante, mas não carregado;
- coerente com a identidade da campanha e do portal da empresa;
- simples de interpretar em uma TV ou tela de gestão;
- responsivo para acesso por celular;
- objetivo, evitando gráficos sem função decisória.

Animações podem ser utilizadas apenas de forma leve, por exemplo na abertura da aplicação. Elementos piscando ou animações repetitivas devem ser evitados.

## 10.2 Visão executiva

Indicadores prioritários:

- valor total recebido durante a campanha;
- valor elegível para cupons;
- quantidade de cupons calculados;
- clientes participantes;
- clientes cadastrados;
- clientes elegíveis;
- valor recuperado de inadimplentes;
- percentual de atingimento de meta;
- data e hora da última atualização.

## 10.3 Evolução da campanha

Gráficos esperados:

- recebimento diário e acumulado;
- evolução mensal dos cupons;
- evolução do número de participantes;
- evolução de clientes inadimplentes para adimplentes;
- valor recuperado ao longo do tempo;
- acompanhamento de meta;
- comparação entre recebimento normal e recuperação.

## 10.4 Distribuições

Filtros e recortes possíveis:

- empresa;
- obra;
- cidade;
- produto;
- mês;
- situação do cliente;
- tipo de pagamento;
- origem do recebimento.

## 10.5 Consulta de cliente

Pode ser criada uma visão para localizar um cliente por CPF, nome, telefone ou venda e apresentar:

- dados cadastrais básicos;
- vendas vinculadas;
- valor pago;
- valor elegível;
- quantidade calculada de cupons;
- status de cadastro;
- status de elegibilidade;
- números oficiais dos cupons, somente quando a integração disponibilizar essa informação.

A interface não deve apresentar números simulados como se fossem cupons oficiais.

---

# 11. Plano de ação de Pedro para a primeira entrega

## Etapa 1 — Preparar o projeto

- criar o repositório ou estrutura local do Streamlit;
- separar configuração, acesso a dados, componentes visuais e páginas;
- configurar variáveis de ambiente e segredos;
- preparar conexão de teste com o Fabric;
- criar tratamento de erro para indisponibilidade da fonte.

Estrutura sugerida:

```text
painel-milhao/
├── app.py
├── pages/
├── components/
├── data/
│   ├── connection.py
│   ├── queries.py
│   └── repository.py
├── services/
│   ├── metrics.py
│   └── validation.py
├── assets/
├── config/
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Etapa 2 — Definir contrato de dados

Antes de construir todos os gráficos, Pedro deve receber ou definir com Carlos e Vinicius:

- nome da view ou tabela;
- granularidade;
- nomes e tipos das colunas;
- campos obrigatórios;
- chave da venda;
- chave do cliente;
- regra de atualização;
- valores possíveis dos status;
- colunas ainda provisórias.

O painel deve depender de um contrato estável, mesmo que a origem continue sendo ajustada.

## Etapa 3 — Construir um MVP com dados controlados

Enquanto a fonte final estiver em desenvolvimento:

- criar uma amostra de dados com a mesma estrutura esperada;
- desenvolver cards e gráficos principais;
- criar filtros básicos;
- validar layout e fluxo de navegação;
- não codificar regras críticas diretamente na interface sem validação.

## Etapa 4 — Integrar com o Fabric

- implementar autenticação segura;
- ler a view consolidada;
- validar tipos de dados;
- tratar nulos e duplicidades;
- configurar cache com TTL;
- apresentar última atualização;
- medir tempo de resposta.

## Etapa 5 — Aplicar identidade visual

- obter materiais oficiais com o Marketing;
- definir paleta e tipografia;
- adaptar a identidade ao padrão visual do portal;
- evitar excesso de dourado, animações e efeitos;
- priorizar contraste e leitura em telas grandes.

## Etapa 6 — Validar indicadores

Para cada métrica exibida, registrar:

- definição;
- fórmula;
- fonte;
- filtros aplicados;
- responsável pela validação;
- exemplo de conferência manual.

Pedro deverá comparar os resultados do painel com amostras fornecidas ou conferidas por Carlos.

## Etapa 7 — Preparar apresentação da primeira versão

A apresentação inicial deve demonstrar:

- conexão com a fonte;
- visão executiva;
- evolução dos recebimentos;
- quantidade de cupons;
- filtros principais;
- atualização automática;
- exemplo de consulta de cliente;
- limitações ainda existentes.

A entrega inicial não deve ser vendida como solução definitiva. Deve ser apresentada como MVP funcional para validação.

---

# 12. Critérios de aceite da primeira entrega

O MVP será considerado pronto para validação quando:

- abrir sem erro no ambiente definido;
- conectar à fonte sem utilizar credenciais expostas;
- apresentar dados da view consolidada;
- exibir data e hora da última atualização;
- possuir indicadores principais;
- permitir filtros básicos;
- responder em tempo aceitável;
- atualizar os dados no intervalo definido;
- apresentar layout compatível com TV e celular;
- permitir conferência de pelo menos um cliente ou venda;
- diferenciar cálculo interno de cupom oficial;
- ter os números aprovados por Carlos em uma amostra controlada;
- listar claramente as regras ainda pendentes.

---

# 13. Pendências que bloqueiam ou afetam Pedro

## Regras de negócio

- confirmar se multa e juros geram cupons;
- confirmar se apenas custas são excluídas;
- definir arredondamento dos valores abaixo de R$ 100;
- definir se saldo residual acumula dentro da venda ou entre meses;
- confirmar tratamento de pagamentos anteriores ao cadastro;
- definir condição de adimplência no fechamento do sorteio;
- confirmar regra para renegociação e antecipação;
- fechar tratamento de vendas com múltiplos compradores;
- definir como ganhadores serão retirados dos sorteios mensais seguintes.

## Dados

- concluir a consulta de Carlos;
- confirmar as tabelas necessárias;
- disponibilizar a view no Fabric;
- definir contrato de colunas;
- garantir ausência de duplicidade por múltiplos compradores;
- definir chave de reconciliação com a plataforma externa;
- disponibilizar cadastro ou aceite do cliente;
- disponibilizar cupons oficiais, caso exista integração.

## Infraestrutura

- definir ambiente de hospedagem;
- definir autenticação do usuário;
- definir acesso do Streamlit ao Fabric;
- avaliar Docker;
- definir frequência de refresh;
- testar concorrência e estabilidade.

## Visual e produto

- receber materiais oficiais da campanha;
- definir identidade visual final;
- confirmar público do painel;
- confirmar se haverá exposição apenas interna;
- confirmar necessidade real de busca individual de cliente;
- definir quais metas serão exibidas.

---

# 14. Riscos principais

## 14.1 Regra incorreta com aparência de dado correto

O maior risco é produzir um painel tecnicamente bonito e numericamente consistente, mas baseado em regra comercial errada.

Toda métrica crítica deve ter validação de negócio e amostra de conferência.

## 14.2 Duplicação por compradores ou junções

Relacionamentos entre venda, pessoas e parcelas podem multiplicar linhas. A quantidade de cupons nunca deve ser calculada depois de uma junção que duplique recebimentos.

## 14.3 Mistura entre cupom calculado e oficial

O painel não pode induzir o usuário a acreditar que uma quantidade simulada já foi registrada pela plataforma externa.

## 14.4 Consulta direta ao UAU

Conectar a aplicação diretamente ao banco operacional cria risco de segurança e desempenho. O acesso deve ocorrer via Fabric ou camada de consumo aprovada.

## 14.5 Escopo visual excessivo

O prazo inicial é curto. Gastar tempo com animações, muitos gráficos ou frontend JavaScript completo pode comprometer a validação dos dados.

## 14.6 Arquitetura provisória virar definitiva

A solução emergencial poderá permanecer em uso. Por isso, mesmo o MVP precisa ter organização mínima, separação de responsabilidades, segredos protegidos e documentação básica.

---

# 15. Decisões técnicas recomendadas para Pedro

1. Usar Streamlit no MVP.
2. Consumir somente uma view ou tabela consolidada no Fabric.
3. Não executar regras financeiras complexas na camada visual.
4. Usar Python apenas para métricas derivadas simples, filtros e apresentação.
5. Separar conexão, transformação e componentes visuais.
6. Configurar cache com TTL explícito.
7. Mostrar sempre a última atualização.
8. Criar validações para colunas ausentes e tipos incorretos.
9. Manter uma página ou seção de auditoria para conferência.
10. Tratar regras ainda não fechadas como parâmetros ou pendências, não como certezas.
11. Evitar expor dados pessoais desnecessários na visão executiva.
12. Registrar versão da regra utilizada para calcular os cupons.

---

# 16. Resultado esperado da primeira entrega

Ao final da primeira entrega, a empresa deverá ter uma aplicação funcional capaz de:

- acompanhar a arrecadação da campanha;
- visualizar a evolução dos pagamentos;
- identificar clientes e vendas participantes;
- estimar ou calcular a quantidade de cupons gerados;
- acompanhar recuperação de inadimplentes;
- filtrar resultados por dimensões relevantes;
- atualizar os dados em intervalos curtos;
- servir como instrumento de gestão e validação;
- evoluir posteriormente para uma aplicação mais robusta.

O foco de Pedro é transformar a base validada pelo time em uma experiência de acompanhamento útil, rápida e confiável. O sucesso do trabalho não será medido pela quantidade de efeitos visuais, mas pela clareza dos indicadores, estabilidade da aplicação e confiança nos números apresentados.
