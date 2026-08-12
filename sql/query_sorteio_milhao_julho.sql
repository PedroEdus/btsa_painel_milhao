-- Base OFICIAL de Julho/2026 - Sorteio 5 Casas & 1 Milhão (Virada de Prêmios)
-- MESMA estrutura e colunas da query principal (query_sorteio_milhao.sql,
--   versão 11/08/2026 com resgate de cessões/quitadas), porém com TODAS as
--   janelas travadas em JULHO. Substitui o snapshot batido em 31/07 como
--   base oficial do mês (incompleto por baixas tardias e sem as regras de
--   cessão - decisão 11/08/2026).
-- Janelas (parametrizadas p/ reuso nos próximos fechamentos):
--   @IniCampanha = 01/07/2026 (fixo, início da campanha)
--   @IniMes      = 01/07/2026 (mês do fechamento)
--   @Corte       = 01/08/2026 (primeiro dia após o fechamento)
--   Para agosto: @IniMes = 01/08, @Corte = 01/09 (@IniCampanha não muda).
-- Diferenças obrigatórias vs query do painel (justificadas):
--   1. APTIDÃO RETROATIVA: parcela vencida até 31/07 em aberto EM 31/07.
--      Reconstrução em 2 fontes (mesma mecânica do fechamento v2):
--      (a) parcela em ContasReceber vencida < 01/08 sem recebimento com
--          Data_Rec < 01/08 (resgate de baixa atrasada: pagou no prazo e
--          a baixa demorou = não conta como aberta);
--      (b) parcela vencida < 01/08 paga só com Data_Rec >= 01/08 = estava
--          aberta no fechamento (pagar em agosto não vira apto de julho).
--   2. DISTRATO/CESSÃO DE AGOSTO NÃO DERRUBAM JULHO: o NOT EXISTS de
--      distrato só exclui distrato efetivo aprovado ANTES de 01/08.
--      Venda distratada em agosto com recebimento em julho ENTRA na
--      base com flag [Distrato Após Fechamento] = 1, porém como NÃO
--      APTO no [Status Sorteio], [Aptidão Casas] e [Aptidão Sorteio],
--      com [Motivo] = DISTRATO APÓS O FECHAMENTO (decisão 11/08/2026:
--      fica visível para auditoria, não concorre).
--   3. Inad Junho: parcela vencida até 30/06 aberta em 31/07 OU paga com
--      Data_Rec >= 01/07 (qualquer data, inclusive agosto+) - mais
--      preciso que a janela de campanha da query do painel.
--   4. Cupons Milhão = acumulado da campanha ATÉ o corte (para julho =
--      próprio julho). Cupons Casas / mês vigente = mês de julho.
--   5. Aptidão em 2 colunas (11/08/2026): [Aptidão Casas] (mensal) -
--      quitada/cedida resgatada só é apta no mês com movimentação;
--      [Aptidão Sorteio] (Milhão/final) - régua retroativa de parcela
--      vencida. [Status Sorteio] mantido por retrocompatibilidade.
-- Regras de cessão (decisão de negócio 11/08/2026 - cada dono tem o seu
--   cupom): venda cedida tem recebimentos cortados em Data_Rec < data da
--   cessão (baixa técnica não vira cupom); cedente (status 1 por cessão)
--   e quitada (status 3) entram se tiverem recebimento na janela.
-- LIMITAÇÕES (valores informativos, não afetam a régua de aptidão):
--   - [Valor a Receber]/[Valor Inadimplência]/juros/multa: calculados
--     sobre parcelas AINDA em ContasReceber hoje (parcela paga em agosto
--     sai do valor, mas o NAO APTO dela segue correto pela fonte (b));
--     ContasReceberCalc_bkp é snapshot D-1, não histórico de 31/07.
--   - [Jurídico Ativo/Passivo] e quantidades de parcela: estado atual.
--   - Venda cadastrada após 31/07 com status 0 aparece com 0 cupons de
--     julho (inofensivo - elegível downstream exige cupom > 0).
-- RODAR na origem (BURITI-BD-02 via gateway) - cross-database com
--   CONTROLADORIA; espelho Fabric não serve. Rodar APÓS as baixas do
--   fechamento terminarem.
-- Empresas excluídas: 3, 204, 226, 229, 301, 302 (mesma lista).
-- Autor: Pedro (11/08/2026), derivada da query principal de Carlos Eduardo

DECLARE @IniCampanha date = '20260701';  -- início da campanha (fixo)
DECLARE @IniMes      date = '20260701';  -- primeiro dia do mês fechado
DECLARE @Corte       date = '20260801';  -- primeiro dia após o fechamento

SELECT
    pc.Cidade                                                   [Cidade],
    REPLACE(pc.Regional, 'REGIONAL', '')                        [Regional],
    pc.Empresa_ven                                              [CodEmpresa],
    pc.Obra_Ven                                                 [CodObra],
    pc.descr_obr                                                [NomeObra],
    pc.Desc_emp                                                 [NomeEmpresa],
    ps.Descricao_psc                                            [Produto],
    pc.Num_Ven                                                  [Venda],
    up.identificador_unid                                       [Identificador],
    FORMAT(pc.Data_Ven, 'dd/MM/yyyy')                           [Dt.Venda],
    FORMAT(pc.ValorTot_Ven, 'C')                                [VlrVenda],
    UPPER(PesCli.Nome_pes)                                      [NomeCliente],
    PesCli.cpf_pes,
    LOWER(PesCli.Email_pes)                                     [EmailCliente],
    TelefoneFormatado,
    TipoTelefone,

    -- Inadimplente EM 31/07 (retroativo: fontes (a) e (b) do cabeçalho)
    CASE
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'Inadimplente'
        ELSE 'Adimplente'
    END                                                         [StatuVenda],

    -- Flag: estava inadimplente em 30/06 (largada da campanha)? 1 = sim
    CASE
        WHEN crConsolidado.ParcelaAbertaAntesJulho = 1
          OR inadJun.NumVend_Rec IS NOT NULL
            THEN 1
        ELSE 0
    END                                                         [Inad Junho],

    -- Flag: pagou EM JULHO parcela depois do vencimento? 1 = recuperação
    CASE
        WHEN recTotais.Recuperou = 1 THEN 1
        ELSE 0
    END                                                         [Recuperação],

    -- Valor recebido em julho de parcelas pagas após o vencimento
    FORMAT(ISNULL(recTotais.ValorRecuperado, 0), 'C')           [Valor Recuperado],

    -- Flag: pagou em julho parcela com vencimento em mês futuro?
    CASE
        WHEN recTotais.Antecipou = 1 THEN 'Sim'
        ELSE 'Não'
    END                                                         [Antecipação],

    -- Valor recebido em julho de parcelas com vencimento em mês futuro
    FORMAT(ISNULL(recTotais.ValorAntecipado, 0), 'C')           [Valor Antecipado],

    -- Quantidade por tipo de parcela (estado atual - informativo)
    crConsolidado.Qtd_P                                         [Qtd Parcelas],
    crConsolidado.Qtd_S                                         [Qtd Sinal],
    crConsolidado.Qtd_SA                                        [Qtd Sinal/Arras],
    crConsolidado.Qtd_SN                                        [Qtd Sinal Negoci],
    crConsolidado.Qtd_E                                         [Qtd Entrada],
    crConsolidado.Qtd_ER                                        [Qtd Ent.Reativacao],
    crConsolidado.Qtd_AM                                        [Qtd Amortizacao],
    crConsolidado.Qtd_FC                                        [Qtd Financ.CEF],
    crConsolidado.Qtd_B                                         [Qtd Balao],
    crConsolidado.Qtd_R                                         [Qtd Residuo],
    crConsolidado.Qtd_I                                         [Qtd Intermediacao],
    crConsolidado.Qtd_OP                                        [Qtd Operacao XPI],

    -- Valores gerais (ver LIMITAÇÕES no cabeçalho)
    FORMAT(ISNULL(crConsolidado.ValorAReceber,     0), 'C')     [Valor a Receber],
    FORMAT(ISNULL(crConsolidado.ValorInadimplente, 0), 'C')     [Valor Inadimplência],
    FORMAT(ISNULL(crConsolidado.ValorJurosInadimplencia, 0), 'C') [Valor Juros Inadimplência],
    FORMAT(ISNULL(crConsolidado.ValorMultaInadimplencia, 0), 'C') [Valor Multa Inadimplência],
    FORMAT(ISNULL(recTotais.ValorRec,              0), 'C')     [Valor Recebido],
    FORMAT(ISNULL(recTotais.ValorCupom,            0), 'C')     [Valor Gera Cupom],
    FORMAT(ISNULL(recTotais.ValorCupomMesAtual,    0), 'C')     [Valor Cupom Mês Atual],
    FORMAT(recTotais.DataUltimoRecebimento, 'dd/MM/yyyy')       [Data Último Recebimento],

    -- Cupons: sorteio do Milhão (acumulado da campanha até o corte,
    -- valor recebido INTEGRAL; clamp evita cupom negativo em estorno)
    IIF(ISNULL(recTotais.ValorRec, 0) > 0,
        FLOOR(ISNULL(recTotais.ValorRec, 0) / 100), 0)          [Cupons Milhão],

    -- Cupons: sorteio das Casas (mês de julho, valor recebido integral)
    IIF(ISNULL(recTotais.ValorRecMesAtual, 0) > 0,
        FLOOR(ISNULL(recTotais.ValorRecMesAtual, 0) / 100), 0)  [Cupons Casas],

    -- Diagnóstico: pagou a parcela de junho (mês anterior ao fechado)?
    CASE
        WHEN parcMesAnt.ParcelaMesPassadoAberta = 1 THEN 'Não'
        ELSE 'Sim'
    END                                                         [Pagou Parcela Mês Anterior],
    DiasAtraso,

    -- Status final do sorteio em 31/07 (Apto / Não Apto).
    -- Distrato efetivo aprovado após o fechamento = NÃO APTO (decisão
    -- 11/08/2026): permanece na base para auditoria, não concorre.
    CASE
        WHEN dist.NumVend_vdd IS NOT NULL
         AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte
            THEN 'NÃO APTO'
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'NÃO APTO'
        ELSE 'APTO'
    END                                                         [Status Sorteio],

    CASE
        WHEN dist.NumVend_vdd IS NOT NULL
         AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte
            THEN 'DISTRATO APÓS O FECHAMENTO'
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'PARCELA VENCIDA EM ABERTO EM 31/07'
        ELSE 'ADIMPLENTE'
    END                                                         [Motivo],

    -- Ocorrência jurídica vinculada à venda (estado atual - informativo)
    CASE WHEN ocor.JuridicoAtivo   = 1 THEN 'Sim' ELSE 'Não' END [Jurídico Ativo],
    CASE WHEN ocor.JuridicoPassivo = 1 THEN 'Sim' ELSE 'Não' END [Jurídico Passivo],

    -- Cessão de direito: esta venda foi gerada por transferência
    CASE WHEN cess.VendaOrigem IS NOT NULL
        THEN 'Sim' ELSE 'Não' END                                [Cessão],
    cess.VendaOrigem                                             [Venda Origem Cessão],
    FORMAT(cess.DataCessao, 'dd/MM/yyyy')                        [Data Cessão],

    -- Quitada (status 3) resgatada por ter recebimento na janela
    CASE WHEN pc.Status_Ven = 3 THEN 'Sim' ELSE 'Não' END        [Contrato Quitado],

    -- Cedente (venda cancelada por cessão): concorre com os cupons
    -- gerados ANTES da cessão (decisão de negócio 11/08/2026)
    CASE WHEN cedida.VendaNova IS NOT NULL
        THEN 'Sim' ELSE 'Não' END                                [Contrato Cedido],
    cedida.VendaNova                                             [Venda Nova Cessão],
    FORMAT(cedida.DataCessao, 'dd/MM/yyyy')                      [Data Cedida],

    -- 1 = distrato efetivo aprovado a partir de 01/08: a venda estava
    -- ativa no fechamento de julho. Permanece na base para auditoria,
    -- mas NÃO APTO nas aptidões (decisão 11/08/2026)
    IIF(dist.NumVend_vdd IS NOT NULL
        AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte,
        1, 0)                                                    [Distrato Após Fechamento],

    -- Sorteio MENSAL (Casas): distrato pós-fechamento = NÃO APTO;
    -- quitada/cedida resgatada só é apta no mês em que teve movimentação
    -- (recebimento no mês fechado); contrato normal segue a régua
    -- retroativa de parcela vencida
    CASE
        WHEN dist.NumVend_vdd IS NOT NULL
         AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte
            THEN 'NÃO APTO'
        WHEN pc.Status_Ven = 3
          OR (pc.Status_Ven = 1 AND cedida.VendaNova IS NOT NULL)
            THEN IIF(ISNULL(recTotais.ValorRecMesAtual, 0) > 0,
                     'APTO', 'NÃO APTO')
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'NÃO APTO'
        ELSE 'APTO'
    END                                                          [Aptidão Casas],

    -- Sorteio FINAL (Milhão): distrato pós-fechamento = NÃO APTO;
    -- demais seguem a régua retroativa de parcela vencida —
    -- quitada/cedida apta com os cupons acumulados (decisão 11/08/2026)
    CASE
        WHEN dist.NumVend_vdd IS NOT NULL
         AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte
            THEN 'NÃO APTO'
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'NÃO APTO'
        ELSE 'APTO'
    END                                                          [Aptidão Sorteio]

FROM
(
    -- Base de vendas ativas (Vendas + VendasRecebidas)
    SELECT
        CASE
            WHEN grpCidade.desc_cger = 'TAQUARALTO' THEN 'PALMAS'
            WHEN grpCidade.desc_cger IS NULL
              OR grpCidade.desc_cger IN ('ADMINISTRATIVO', 'INVESTIMENTOS',
                                         'GERENCIAIS/INTERNAS', 'CONTROLADAS',
                                         'NOVOS NEGOCIOS', 'NOVOS NEGÓCIOS',
                                         'BURITI AGRO-FAZENDAS')
              OR grpCidade.desc_cger LIKE 'HOLDING%'
                THEN ISNULL(NULLIF(UPPER(o.cid_obr), ''), grpCidade.desc_cger)
            ELSE grpCidade.desc_cger
        END                                             AS Cidade,
        grpRegional.desc_cger                           AS Regional,
        v.Empresa_ven,
        v.Obra_Ven,
        v.Num_Ven,
        v.Data_Ven,
        ValorTot_Ven,
        v.Status_Ven,
        ValorTot_Ven                                    AS Faturamento,
        o.descr_obr,
        e.Desc_emp,
        v.Cliente_Ven
    FROM
    (
        SELECT
            Empresa_ven, Obra_ven, Num_Ven, Data_Ven, DataCad_Ven, Status_ven,
            Cliente_Ven,
            ValorTot_Ven + Acrescimo_Ven - Desconto_Ven AS ValorTot_Ven
        FROM Vendas
        WHERE  LEFT(Obra_ven, 2) IN ('65','67','68','69')

        UNION

        SELECT
            Empresa_vrec, Obra_VRec, Num_VRec, Data_VRec, DataCad_Vrec, Status_Vrec,
            Cliente_VRec,
            ValorTot_VRec + Acrescimo_VRec - Desconto_VRec AS ValorTot_VRec
        FROM VendasRecebidas
        WHERE LEFT(Obra_VRec, 2) IN ('65','67','68','69')
          -- Venda em transição presente nas duas tabelas: vale a linha de
          -- Vendas (fonte viva) - evita duplicata no resgate de quitadas
          AND NOT EXISTS (
                SELECT 1 FROM Vendas v0
                WHERE v0.Empresa_ven = VendasRecebidas.Empresa_vrec
                  AND v0.Obra_ven    = VendasRecebidas.Obra_VRec
                  AND v0.Num_Ven     = VendasRecebidas.Num_VRec
          )

    ) AS v

    INNER JOIN Obras o
        ON  o.Empresa_obr = v.Empresa_ven
        AND o.cod_obr     = v.Obra_Ven

    INNER JOIN Empresas e
        ON  e.Codigo_emp  = o.Empresa_obr

    LEFT JOIN GruposDeObra AS grpFilho
        ON  grpFilho.Codigo_cger = o.CodGrupo_obr

    LEFT JOIN GruposDeObra AS grpCidade
        ON  grpCidade.Codigo_cger = LEFT(grpFilho.Codigo_cger, 7)

    LEFT JOIN GruposDeObra AS grpRegional
        ON  grpRegional.Codigo_cger = LEFT(grpFilho.Codigo_cger, 3)

    GROUP BY
        grpCidade.desc_cger,
        grpRegional.desc_cger,
        o.cid_obr,
        v.Empresa_ven, v.Obra_Ven, v.Num_Ven,
        v.Data_Ven, ValorTot_Ven, v.Status_Ven,
        o.descr_obr, e.Desc_emp, v.Cliente_Ven

) AS pc

-- --------------------------------------------------------
-- INNER JOIN: Itens da venda (1 linha por venda; ItensRecebidas só
-- entra via anti-join se não houver registro em ItensVenda)
-- --------------------------------------------------------
INNER JOIN
(
    SELECT Empresa_itv, Obra_itv, NumVend_Itv, Produto_itv, CodPerson_itv
    FROM
    (
        SELECT
            Empresa_itv, Obra_itv, NumVend_Itv, Produto_itv, CodPerson_itv,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_itv, Obra_itv, NumVend_Itv
                ORDER BY (SELECT NULL)
            ) AS rn
        FROM ItensVenda
    ) AS iv
    WHERE iv.rn = 1

    UNION ALL

    SELECT Empresa_itr, Obra_itr, NumVend_itr, Produto_itr, CodPerson_itr
    FROM
    (
        SELECT
            Empresa_itr, Obra_itr, NumVend_itr, Produto_itr, CodPerson_itr,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_itr, Obra_itr, NumVend_itr
                ORDER BY (SELECT NULL)
            ) AS rn
        FROM ItensRecebidas ir
        WHERE NOT EXISTS (
            SELECT 1 FROM ItensVenda iv2
            WHERE iv2.Empresa_itv = ir.Empresa_itr
              AND iv2.Obra_itv    = ir.Obra_itr
              AND iv2.NumVend_Itv = ir.NumVend_itr
        )
    ) AS ir2
    WHERE ir2.rn = 1
) AS itv
    ON  itv.Empresa_itv = pc.Empresa_ven
    AND itv.Obra_itv    = pc.Obra_Ven
    AND itv.NumVend_Itv = pc.Num_Ven


-- LEFT JOIN: Unidade/Personalização

LEFT JOIN
(
    SELECT Empresa_unid, Obra_unid, Prod_unid, NumPer_unid, identificador_unid
    FROM UnidadePer
    WHERE Vendido_unid <> 10 AND  LEFT(Obra_unid, 2) IN ('65','67','68','69')
) AS up
    ON  up.Empresa_unid = itv.Empresa_itv
    AND up.Obra_unid    = itv.Obra_itv
    AND up.Prod_unid    = itv.Produto_itv
    AND up.Numper_unid  = itv.CodPerson_itv


-- LEFT JOIN: Nome do Produto

LEFT JOIN PrdSrv AS ps
    ON ps.NumProd_psc = up.Prod_unid
    AND Status_psc = 1


-- LEFT JOIN: Cliente

LEFT JOIN Pessoas AS PesCli
    ON PesCli.cod_pes = pc.Cliente_Ven


-- LEFT JOIN: Melhor telefone por pessoa

LEFT JOIN
(
    SELECT
        classificado.pes_tel,
        classificado.NumeroTratado  AS TelefoneFormatado,
        classificado.TipoTel        AS TipoTelefone
    FROM
    (
        SELECT
            base.pes_tel,
            base.NumeroCompleto,
            base.FoneLimpo,

            CASE
                WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                    THEN base.NumeroCompleto
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                    THEN base.DddLimpo + '9' + base.FoneLimpo
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                    THEN base.NumeroCompleto
                ELSE base.NumeroCompleto
            END AS NumeroTratado,

            CASE
                WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                    THEN 'Celular'
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                    THEN 'Celular (corrigido)'
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                    THEN 'Fixo'
                ELSE 'Indefinido'
            END AS TipoTel,

            ROW_NUMBER() OVER (
                PARTITION BY base.pes_tel
                ORDER BY
                    CASE
                        WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                            THEN 1
                        WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                            THEN 2
                        WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                            THEN 3
                        ELSE 4
                    END
            ) AS prioridade

        FROM
        (
            SELECT
                pt.pes_tel,
                SUBSTRING(
                    REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')',''),
                    PATINDEX('%[1-9]%', REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')','') + '1'),
                    LEN(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')',''))
                ) AS DddLimpo,
                SUBSTRING(
                    REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')',''),
                    PATINDEX('%[1-9]%', REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')','') + '1'),
                    LEN(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')',''))
                ) AS FoneLimpo
            FROM PesTel AS pt
        ) AS base0
        CROSS APPLY (
            SELECT  base0.pes_tel,
                    base0.DddLimpo,
                    base0.FoneLimpo,
                    base0.DddLimpo + base0.FoneLimpo AS NumeroCompleto
        ) AS base

    ) AS classificado
    WHERE classificado.prioridade = 1

) AS tel
    ON tel.pes_tel = pc.Cliente_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Ocorrência jurídica vinculada à venda (Ativo/Passivo)
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        Empresa_ocv,
        NumDoc_ocv,
        SUM(CASE WHEN NumOco_ocv = 4  THEN 1 ELSE 0 END) AS JuridicoAtivo,
        SUM(CASE WHEN NumOco_ocv = 32 THEN 1 ELSE 0 END) AS JuridicoPassivo
    FROM OcorrenciaVinculo
    WHERE Status_ocv = 0
      AND NumOco_ocv IN (4, 32)
    GROUP BY NumDoc_ocv, Empresa_ocv
) AS ocor
    ON  ocor.Empresa_ocv = pc.Empresa_ven
    AND ocor.NumDoc_ocv  = CONCAT('VENDAS ', pc.Num_Ven, '-', pc.Obra_Ven)


-- --------------------------------------------------------
-- LEFT JOIN: Cessão de direito - venda ORIUNDA de transferência
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        Empresa_vhist,
        Obra_vhist,
        NumNovaVend_vhist,
        MAX(NumVend_vhist)  AS VendaOrigem,
        MAX(DataMnt_vhist)  AS DataCessao
    FROM VendaHist
    WHERE TipoMnt_vhist = 2
      AND DataAprovacao_vhist IS NOT NULL
      AND NumNovaVend_vhist IS NOT NULL
      AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
    GROUP BY Empresa_vhist, Obra_vhist, NumNovaVend_vhist
) AS cess
    ON  cess.Empresa_vhist     = pc.Empresa_ven
    AND cess.Obra_vhist        = pc.Obra_Ven
    AND cess.NumNovaVend_vhist = pc.Num_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Cessão de direito - venda CEDIDA (lado do cedente)
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        Empresa_vhist,
        Obra_vhist,
        NumVend_vhist,
        MAX(NumNovaVend_vhist) AS VendaNova,
        MAX(DataMnt_vhist)     AS DataCessao
    FROM VendaHist
    WHERE TipoMnt_vhist = 2
      AND DataAprovacao_vhist IS NOT NULL
      AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
    GROUP BY Empresa_vhist, Obra_vhist, NumVend_vhist
) AS cedida
    ON  cedida.Empresa_vhist = pc.Empresa_ven
    AND cedida.Obra_vhist    = pc.Obra_Ven
    AND cedida.NumVend_vhist = pc.Num_Ven


-- --------------------------------------------------------
-- LEFT JOIN: ContasReceber consolidado - APTIDÃO RETROATIVA 31/07.
-- Fonte (a): parcela vencida < @Corte ainda em ContasReceber SEM
-- recebimento com Data_Rec < @Corte (anti-join pagas = resgate de
-- baixa atrasada). Valores de inadimplência: mesma condição
-- (ver LIMITAÇÕES no cabeçalho). DiasAtraso relativo a 31/07.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        cr.Empresa_prc,
        cr.Obra_prc,
        cr.NumVend_prc,

        SUM(IIF(cr.Tipo_Prc = 'P',  1, 0))   AS Qtd_P,
        SUM(IIF(cr.Tipo_Prc = 'S',  1, 0))   AS Qtd_S,
        SUM(IIF(cr.Tipo_Prc = 'SA', 1, 0))   AS Qtd_SA,
        SUM(IIF(cr.Tipo_Prc = 'SN', 1, 0))   AS Qtd_SN,
        SUM(IIF(cr.Tipo_Prc = 'E',  1, 0))   AS Qtd_E,
        SUM(IIF(cr.Tipo_Prc = 'ER', 1, 0))   AS Qtd_ER,
        SUM(IIF(cr.Tipo_Prc = 'AM', 1, 0))   AS Qtd_AM,
        SUM(IIF(cr.Tipo_Prc = 'FC', 1, 0))   AS Qtd_FC,
        SUM(IIF(cr.Tipo_Prc = 'B',  1, 0))   AS Qtd_B,
        SUM(IIF(cr.Tipo_Prc = 'R',  1, 0))   AS Qtd_R,
        SUM(IIF(cr.Tipo_Prc = 'I',  1, 0))   AS Qtd_I,
        SUM(IIF(cr.Tipo_Prc = 'OP', 1, 0))   AS Qtd_OP,

        SUM(IIF(cr.Tipo_Prc <> '1', crc.ValParcela_crc, 0))   AS ValorAReceber,

        -- Aberta em 31/07 (fonte a): vencida < @Corte sem baixa de julho
        MAX(
            CASE
                WHEN cr.Data_Prc < @Corte
                 AND pagas.NumVend_Rec IS NULL
                    THEN 'Inadimplente'
            END
        )                                     AS StatusContasReceber,

        -- Vencida até 30/06 ainda aberta em 31/07 (flag Inad Junho)
        MAX(
            CASE
                WHEN cr.Data_Prc < @IniCampanha
                 AND pagas.NumVend_Rec IS NULL
                    THEN 1
            END
        )                                     AS ParcelaAbertaAntesJulho,

        -- Dias de atraso na data do fechamento (31/07)
        DATEDIFF(DAY,
            MIN(
                CASE
                    WHEN cr.Data_Prc < @Corte
                     AND pagas.NumVend_Rec IS NULL
                        THEN cr.Data_Prc
                END
            ),
            DATEADD(DAY, -1, @Corte)
        )                                     AS DiasAtraso,

        -- SEM custas (Tipo '1') - padrão BI Carteira Migração
        SUM(
            CASE
                WHEN cr.Data_Prc < @Corte
                 AND pagas.NumVend_Rec IS NULL
                 AND cr.Tipo_Prc <> '1'
                    THEN ISNULL(crc.ValPrincipal_crc, 0)
                       + ISNULL(crc.ValJurosComp_crc, 0)
                       + ISNULL(crc.ValCorrecao_crc, 0)
                ELSE 0
            END
        )                                     AS ValorInadimplente,

        SUM(
            CASE
                WHEN cr.Data_Prc < @Corte
                 AND pagas.NumVend_Rec IS NULL
                 AND cr.Tipo_Prc <> '1'
                    THEN ISNULL(crc.ValJuroAtraso_crc, 0)
                ELSE 0
            END
        )                                     AS ValorJurosInadimplencia,

        SUM(
            CASE
                WHEN cr.Data_Prc < @Corte
                 AND pagas.NumVend_Rec IS NULL
                 AND cr.Tipo_Prc <> '1'
                    THEN ISNULL(crc.ValMultaAtraso_crc, 0)
                ELSE 0
            END
        )                                     AS ValorMultaInadimplencia

    FROM ContasReceber cr
    LEFT JOIN CONTROLADORIA.dbo.ContasReceberCalc_bkp crc
        ON  crc.Empresa_crc    = cr.Empresa_prc
        AND crc.Obra_crc       = cr.Obra_Prc
        AND crc.NumVend_crc    = cr.NumVend_prc
        AND crc.NumParc_crc    = cr.NumParc_Prc
        AND crc.NumParcGer_crc = cr.NumParcGer_Prc
        AND crc.Tipo_crc       = cr.Tipo_Prc
    -- Parcela com recebimento ATÉ 31/07 = estava paga no fechamento
    -- (resgate de baixa atrasada: Data_Rec preserva a data real)
    LEFT JOIN
    (
        SELECT DISTINCT
            Empresa_rec, Obra_Rec, NumVend_Rec,
            NumParc_Rec, NumParcGer_Rec, Tipo_Rec
        FROM Recebidas
        WHERE CAST(Data_Rec AS DATE) < @Corte
          AND LEFT(Obra_rec, 2) IN ('65','67','68','69')
    ) AS pagas
        ON  pagas.Empresa_rec    = cr.Empresa_prc
        AND pagas.Obra_Rec       = cr.Obra_Prc
        AND pagas.NumVend_Rec    = cr.NumVend_prc
        AND pagas.NumParc_Rec    = cr.NumParc_Prc
        AND pagas.NumParcGer_Rec = cr.NumParcGer_Prc
        AND pagas.Tipo_Rec       = cr.Tipo_Prc
    WHERE LEFT(cr.Obra_Prc, 2) IN ('65','67','68','69')
    GROUP BY cr.Empresa_prc, cr.Obra_prc, cr.NumVend_prc

) AS crConsolidado
    ON  crConsolidado.Empresa_prc = pc.Empresa_ven
    AND crConsolidado.Obra_prc    = pc.Obra_Ven
    AND crConsolidado.NumVend_prc = pc.Num_Ven


-- --------------------------------------------------------
-- Fonte (b) da aptidão retroativa: parcela vencida até 31/07 paga
-- só a partir de 01/08 = estava vencida e aberta no fechamento
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT DISTINCT
        r.Empresa_rec,
        r.Obra_Rec,
        r.NumVend_Rec
    FROM Recebidas r
    WHERE LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
      AND CAST(r.DataVenci_Rec AS DATE) < @Corte
      AND CAST(r.Data_Rec     AS DATE) >= @Corte
) AS pagasDepois
    ON  pagasDepois.Empresa_rec = pc.Empresa_ven
    AND pagasDepois.Obra_Rec    = pc.Obra_Ven
    AND pagasDepois.NumVend_Rec = pc.Num_Ven


-- --------------------------------------------------------
-- Inad Junho, componente pago: parcela vencida até 30/06 paga em
-- QUALQUER data >= 01/07 (inclusive agosto+) = estava inadimplente
-- na largada da campanha
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT DISTINCT
        r.Empresa_rec,
        r.Obra_Rec,
        r.NumVend_Rec
    FROM Recebidas r
    WHERE LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
      AND CAST(r.DataVenci_Rec AS DATE) < @IniCampanha
      AND CAST(r.Data_Rec     AS DATE) >= @IniCampanha
) AS inadJun
    ON  inadJun.Empresa_rec = pc.Empresa_ven
    AND inadJun.Obra_Rec    = pc.Obra_Ven
    AND inadJun.NumVend_Rec = pc.Num_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Valores recebidos na janela (@IniCampanha até @Corte -
-- para julho, o próprio mês). Composições idênticas à query principal.
-- Venda cedida: recebimento só conta até a VÉSPERA da cessão (baixa
-- técnica não é pagamento do cedente - decisão 11/08/2026).
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        r.Empresa_rec,
        r.Obra_rec,
        r.NumVend_rec,

        SUM((
              r.ValorConf_Rec
            + r.VlJurosParcConf_Rec
            + r.VlCorrecaoConf_Rec
            + r.VlAcresConf_Rec
            + r.VlTaxaBolConf_Rec
            + r.VlMultaConf_Rec
            + r.VlJurosConf_Rec
            + r.VlCorrecaoAtrConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoCustaConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorRec,

        SUM((
              r.ValorConf_Rec
            + r.VlJurosParcConf_Rec
            + r.VlCorrecaoConf_Rec
            + r.VlAcresConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorCupom,

        SUM(CASE
                WHEN CAST(r.Data_Rec AS DATE) >= @IniMes
                THEN (
                      r.ValorConf_Rec
                    + r.VlJurosParcConf_Rec
                    + r.VlCorrecaoConf_Rec
                    + r.VlAcresConf_Rec
                ) - (
                      r.VlDescontoConf_Rec
                    + r.ValDescontoImpostoConf_Rec
                    + r.ValDescontoCondicionalConf_rec
                )
                ELSE 0
            END)                        AS ValorCupomMesAtual,

        SUM(CASE
                WHEN CAST(r.Data_Rec AS DATE) >= @IniMes
                THEN (
                      r.ValorConf_Rec
                    + r.VlJurosParcConf_Rec
                    + r.VlCorrecaoConf_Rec
                    + r.VlAcresConf_Rec
                    + r.VlTaxaBolConf_Rec
                    + r.VlMultaConf_Rec
                    + r.VlJurosConf_Rec
                    + r.VlCorrecaoAtrConf_Rec
                ) - (
                      r.VlDescontoConf_Rec
                    + r.ValDescontoCustaConf_Rec
                    + r.ValDescontoImpostoConf_Rec
                    + r.ValDescontoCondicionalConf_rec
                )
                ELSE 0
            END)                        AS ValorRecMesAtual,

        MAX(CASE
                WHEN EOMONTH(r.Data_Rec) < EOMONTH(r.DataVenci_Rec)
                THEN 1
                ELSE 0
            END)                        AS Antecipou,

        SUM(CASE
                WHEN EOMONTH(r.Data_Rec) < EOMONTH(r.DataVenci_Rec)
                THEN (
                      r.ValorConf_Rec
                    + r.VlJurosParcConf_Rec
                    + r.VlCorrecaoConf_Rec
                    + r.VlAcresConf_Rec
                    + r.VlTaxaBolConf_Rec
                    + r.VlMultaConf_Rec
                    + r.VlJurosConf_Rec
                    + r.VlCorrecaoAtrConf_Rec
                ) - (
                      r.VlDescontoConf_Rec
                    + r.ValDescontoCustaConf_Rec
                    + r.ValDescontoImpostoConf_Rec
                    + r.ValDescontoCondicionalConf_rec
                )
                ELSE 0
            END)                        AS ValorAntecipado,

        MAX(CASE
                WHEN CAST(r.Data_Rec AS DATE) > CAST(r.DataVenci_Rec AS DATE)
                THEN 1
                ELSE 0
            END)                        AS Recuperou,

        SUM(CASE
                WHEN CAST(r.Data_Rec AS DATE) > CAST(r.DataVenci_Rec AS DATE)
                THEN (
                      r.ValorConf_Rec
                    + r.VlJurosParcConf_Rec
                    + r.VlCorrecaoConf_Rec
                    + r.VlAcresConf_Rec
                    + r.VlTaxaBolConf_Rec
                    + r.VlMultaConf_Rec
                    + r.VlJurosConf_Rec
                    + r.VlCorrecaoAtrConf_Rec
                ) - (
                      r.VlDescontoConf_Rec
                    + r.ValDescontoCustaConf_Rec
                    + r.ValDescontoImpostoConf_Rec
                    + r.ValDescontoCondicionalConf_rec
                )
                ELSE 0
            END)                        AS ValorRecuperado,

        MAX(r.Data_Rec)                 AS DataUltimoRecebimento
    FROM Recebidas r
    LEFT JOIN
    (
        SELECT Empresa_vhist, Obra_vhist, NumVend_vhist,
               MAX(DataMnt_vhist) AS DataCessao
        FROM VendaHist
        WHERE TipoMnt_vhist = 2
          AND DataAprovacao_vhist IS NOT NULL
          AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
        GROUP BY Empresa_vhist, Obra_vhist, NumVend_vhist
    ) AS ced
        ON  ced.Empresa_vhist = r.Empresa_rec
        AND ced.Obra_vhist    = r.Obra_rec
        AND ced.NumVend_vhist = r.NumVend_rec
    WHERE CAST(r.Data_Rec AS DATE) >= @IniCampanha
      AND CAST(r.Data_Rec AS DATE) <  @Corte
      AND r.Tipo_rec <> '1'
      AND LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
      AND (ced.DataCessao IS NULL
           OR CAST(r.Data_Rec AS DATE) < CAST(ced.DataCessao AS DATE))
    GROUP BY r.Empresa_rec, r.Obra_rec, r.NumVend_rec

) AS recTotais
    ON  recTotais.Empresa_rec = pc.Empresa_ven
    AND recTotais.Obra_rec    = pc.Obra_Ven
    AND recTotais.NumVend_rec = pc.Num_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Tem parcela de junho (mês anterior ao fechado) que
-- estava em aberto em 31/07? (diagnóstico, com resgate de baixa)
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT DISTINCT
        cr.Empresa_prc,
        cr.Obra_prc,
        cr.NumVend_prc,
        1 AS ParcelaMesPassadoAberta
    FROM ContasReceber cr
    WHERE cr.Tipo_Prc <> '1'
      AND LEFT(cr.Obra_Prc, 2) IN ('65','67','68','69')
      AND cr.Data_Prc >= DATEADD(MONTH, -1, @IniMes)
      AND cr.Data_Prc <  @IniMes
      AND NOT EXISTS (
            SELECT 1 FROM Recebidas r
            WHERE r.Empresa_rec    = cr.Empresa_prc
              AND r.Obra_Rec       = cr.Obra_Prc
              AND r.NumVend_Rec    = cr.NumVend_prc
              AND r.NumParc_Rec    = cr.NumParc_Prc
              AND r.NumParcGer_Rec = cr.NumParcGer_Prc
              AND r.Tipo_Rec       = cr.Tipo_Prc
              AND CAST(r.Data_Rec AS DATE) < @Corte
      )
) AS parcMesAnt
    ON  parcMesAnt.Empresa_prc = pc.Empresa_ven
    AND parcMesAnt.Obra_prc    = pc.Obra_Ven
    AND parcMesAnt.NumVend_prc = pc.Num_Ven


-- --------------------------------------------------------
-- Último distrato EFETIVO e APROVADO da venda (flag Distrato Após
-- Fechamento + ramo de resgate no WHERE)
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        d.Empresa_vdd,
        d.Obra_vdd,
        d.NumVend_vdd,
        d.DataCad_vdd,
        d.DataAprov_vdd
    FROM
    (
        SELECT
            Empresa_vdd, Obra_vdd, NumVend_vdd, DataCad_vdd, DataAprov_vdd,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_vdd, Obra_vdd, NumVend_vdd
                ORDER BY DataCad_vdd DESC, Num_vdd DESC
            ) AS rn
        FROM VendaDistrato
        WHERE TipoAditivo_vdd = 0
          AND StatusAprov_vdd = 1
    ) AS d
    WHERE d.rn = 1
) AS dist
    ON  dist.Empresa_vdd = pc.Empresa_ven
    AND dist.Obra_vdd    = pc.Obra_Ven
    AND dist.NumVend_vdd = pc.Num_Ven

-- --------------------------------------------------------
-- Pertencimento à base de JULHO:
--   status 0 = ativa;
--   status 3 (quitada) com recebimento na janela = segue concorrendo;
--   status 1 cedida com recebimento real pré-cessão = cedente;
--   status 1 distratada APÓS o fechamento com recebimento na janela =
--     estava ativa em 31/07 (flag exposto, decisão dos 92 downstream).
-- Distrato efetivo aprovado ANTES de 01/08 exclui (estava fora na foto).
-- --------------------------------------------------------
WHERE (
        pc.Status_Ven = 0
        OR (pc.Status_Ven = 3 AND recTotais.NumVend_rec IS NOT NULL)
        OR (pc.Status_Ven = 1
            AND cedida.VendaNova IS NOT NULL
            AND recTotais.NumVend_rec IS NOT NULL)
        OR (pc.Status_Ven = 1
            AND dist.NumVend_vdd IS NOT NULL
            AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte
            AND recTotais.NumVend_rec IS NOT NULL)
      )
  AND pc.Empresa_ven NOT IN (3, 204, 226, 229, 301, 302)

  AND NOT EXISTS (
        SELECT 1
        FROM VendaDistrato vdd
        WHERE vdd.Empresa_vdd      = pc.Empresa_ven
          AND vdd.obra_vdd         = pc.Obra_Ven
          AND vdd.NumVend_vdd      = pc.Num_Ven
          AND vdd.TipoAditivo_vdd  = 0
          AND vdd.StatusAprov_vdd  = 1
          AND CAST(COALESCE(vdd.DataAprov_vdd, vdd.DataCad_vdd) AS DATE) < @Corte
  )

ORDER BY pc.Cidade, pc.Regional, pc.Obra_Ven;
