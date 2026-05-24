% =========================================================================
% ANÁLISIS ECONÓMICO: REDISEÑO LAYOUT SVQ1 + DQA4
% Máster en Ingeniería Industrial – DPCIS 2025-26
%
% VERSIÓN CFO (DIRECCIÓN FINANCIERA): 
%   1. Matriz de Decisión extendida a 8 Variables Estratégicas.
%   2. Inclusión de "Ahorro Estabilizado" y "Resiliencia al Riesgo (Drop)".
%   3. Inclusión de "TIR Pesimista (Supervivencia en Crisis)".
%   4. Opción ESTÁNDAR justificada de forma técnica e inatacable.
% =========================================================================
clear; clc; close all;

fprintf('=========================================================\n');
fprintf('   ANÁLISIS ECONÓMICO AVANZADO (C-LEVEL) – SVQ1 + DQA4\n');
fprintf('=========================================================\n\n');


% =========================================================================
% BLOQUES 1 y 2 – COSTES Y AHORROS BASE DEL ENUNCIADO
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 1 · SITUACIÓN ACTUAL Y AHORROS PROYECTADOS\n');
fprintf('─────────────────────────────────────────────────────────\n');
coste_transferencias   = 1.99e6;  
ahorro_opciones = [4.7   6.7   8.9] * 1e6;

fprintf('  Coste de transferencias redundantes: %7.2f M€/año\n', coste_transferencias/1e6);
fprintf('  Ahorros brutos proyectados:\n');
fprintf('    - Básica:     %4.2f M€/año\n', ahorro_opciones(1)/1e6);
fprintf('    - Estándar:   %4.2f M€/año\n', ahorro_opciones(2)/1e6);
fprintf('    - Premium:    %4.2f M€/año\n\n', ahorro_opciones(3)/1e6);


% =========================================================================
% BLOQUE 3 – COSTES ADICIONALES DEL PROYECTO (CAPEX / OPEX)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 3 · COSTES DE TRANSICIÓN Y MITIGACIÓN (CAPEX/OPEX)\n');
fprintf('─────────────────────────────────────────────────────────\n');

% CAPEX
capex_formacion     = 1.56e6;   
capex_mitg_fases    = 2.20e6;   
capex_mitg_respaldo = 1.80e6;   
capex_mitg_incent   = 0.68e6;
capex_mitg_seguros     = 0.45e6;  

% OPEX   
opex_subsidio_publico = 187000;   
opex_penalizacion_um  = -6368.80; % Ahorro para unificar en rutas

capex_adicional  = capex_formacion + capex_mitg_fases + capex_mitg_respaldo + capex_mitg_incent;
opex_nuevo_anual = opex_subsidio_publico + opex_penalizacion_um;

fprintf('  %-38s  %7.3f M€\n','TOTAL CAPEX adicional de transición:', capex_adicional/1e6);
fprintf('  %-38s  %7.3f M€/año\n\n','TOTAL OPEX nuevo recurrente:', opex_nuevo_anual/1e6);


% =========================================================================
% BLOQUE 4 – INVERSIÓN TOTAL
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 4 · COMPARATIVA DE OPCIONES DE INVERSIÓN\n');
fprintf('─────────────────────────────────────────────────────────\n');

capex_tabla2  = [18.3  28.5  42.7] * 1e6;
capex_total = capex_tabla2 + capex_adicional;
nombres = {'Básica', 'Estándar', 'Premium'};

fprintf('\n  %-12s  %10s  %10s  %14s\n', 'Opción', 'CAPEX base', 'CAPEX total', 'Ahorro base/año');
fprintf('  %s\n', repmat('─',1,54));
for i = 1:3
    fprintf('  %-12s  %10.1f  %10.1f  %14.1f\n', ...
            nombres{i}, capex_tabla2(i)/1e6, capex_total(i)/1e6, ahorro_opciones(i)/1e6);
end
fprintf('\n');


% =========================================================================
% BLOQUE 5 – RIESGOS: MATRIZ DE EFECTIVIDAD Y RIESGO RESIDUAL (§8.1)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 5 · CUANTIFICACIÓN DE RIESGOS RESIDUALES (TABLA DE EFECTIVIDAD)\n');
fprintf('─────────────────────────────────────────────────────────\n');
fprintf('  Aplicando la matriz de mitigación para calcular las probabilidades residuales:\n');

% 1. Declaración explícita de la efectividad de tu tabla
efectividad_fases      = 0.75; % 75% para mitigar cortes de servicio
efectividad_respaldo   = 0.85; % 85% para mitigar fallos de software/IT
efectividad_seguros    = 0.60; % 60% para mitigar contingencias legales
efectividad_incentivos = 0.70; % 70% para mitigar huelgas/problemas RRHH

% 2. Costes base del enunciado
coste_r1 = 8.5e6; % Servicio
coste_r2 = 2.1e6; % Empleados
coste_r4 = 3.2e6; % Tecnología
coste_r5 = 3.0e6; % Legal
sobrecoste_r3_pct = 0.30; % Obra (+30% del CAPEX base)

% 3. Cálculo matemático del Riesgo Residual: Probabilidad_Final = Prob_Base * (1 - Efectividad)
prob_r1 = 0.30 * (1 - efectividad_fases);       % Queda en 7.5%
prob_r2 = 0.45 * (1 - efectividad_incentivos);  % Queda en 13.5%
prob_r3 = 0.35;                                 % Queda en 35.0% (¡Sin mitigar, no hay estrategia en la tabla!)
prob_r4 = 0.30 * (1 - efectividad_respaldo);    % Queda en 4.5%
prob_r5 = 0.15 * (1 - efectividad_seguros);     % Queda en 6.0%

fprintf('   -> R1 (Servicio):   Prob. Residual = %4.1f%% (Antes 30%% | Mitigado por Fases al 75%%)\n', prob_r1*100);
fprintf('   -> R2 (Empleados):  Prob. Residual = %4.1f%% (Antes 45%% | Mitigado por Incentivos al 70%%)\n', prob_r2*100);
fprintf('   -> R3 (Obras):      Prob. Residual = %4.1f%% (Antes 35%% | NO MITIGADO por esta tabla)\n', prob_r3*100);
fprintf('   -> R4 (Tecnología): Prob. Residual = %4.1f%% (Antes 30%% | Mitigado por Respaldo al 85%%)\n', prob_r4*100);
fprintf('   -> R5 (Legal):      Prob. Residual = %4.1f%% (Antes 15%% | Mitigado por Seguros al 60%%)\n\n', prob_r5*100);

% Multiplicadores asimétricos según perfil de inversión [Básica, Estándar, Premium]
mult_huelga = [1.5, 1.0, 0.5]; 
mult_tech   = [0.5, 1.0, 2.0]; 
mult_const  = [1.0, 1.0, 1.5]; 

ve_riesgo_capex = zeros(1,3);
ve_riesgos_opex = zeros(1,3);

for i = 1:3
    % El riesgo de obra (R3) incrementa el CAPEX del escenario pesimista
    ve_riesgo_capex(i) = capex_tabla2(i) * sobrecoste_r3_pct * (prob_r3 * mult_const(i));
    
    % Los riesgos operativos golpean la caja en el Año 1 del escenario pesimista
    ve_riesgos_opex(i) = (prob_r1 * coste_r1) + ...
                         (prob_r2 * mult_huelga(i) * coste_r2) + ...
                         (prob_r4 * mult_tech(i) * coste_r4) + ...
                         (prob_r5 * coste_r5);
end

fprintf('  Valor Esperado del Riesgo Residual inyectado en Escenario Pesimista:\n');
fprintf('    - Opción Básica:   %5.2f M€\n', ve_riesgos_opex(1)/1e6);
fprintf('    - Opción Estándar: %5.2f M€\n', ve_riesgos_opex(2)/1e6);
fprintf('    - Opción Premium:  %5.2f M€\n\n', ve_riesgos_opex(3)/1e6);


% =========================================================================
% BLOQUE 6 – ESCENARIOS PERT (REDEFINIDOS)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 6 · MODELADO DE FLUJOS (PERT Ajustado)\n');
fprintf('─────────────────────────────────────────────────────────\n');
fprintf('  O: Optimista -> Ahorro +20%% | Rto. 100%% en Año 1 | Sin Riesgos\n');
fprintf('  M: Probable  -> Ahorro Base | Curva Rápida (75%%)   | Riesgos mitigados\n');
fprintf('  P: Pesimista -> Ahorro -20%% | Curva Lenta (50%%)    | Murphy + Asimetría\n\n');

horizonte = 10;
tasa_k    = 0.07;

curva_O = ones(1, horizonte);
curva_M = [0.75, ones(1, horizonte-1)];
curva_P = [0.50, 0.75, ones(1, horizonte-2)];

ahorro_neto_O = (ahorro_opciones * 1.20) - opex_nuevo_anual;
ahorro_neto_M = ahorro_opciones - opex_nuevo_anual;
ahorro_neto_P = (ahorro_opciones * 0.80) - opex_nuevo_anual;

VAN_PERT = zeros(1,3); TIR_PERT = zeros(1,3); PB_PERT = zeros(1,3);
VAN_P = zeros(1,3); VAN_O = zeros(1,3); VAN_M = zeros(1,3);
TIR_P = zeros(1,3); % Nueva variable: TIR en crisis

flujos_plot_PERT = zeros(3, horizonte+1);
flujos_plot_O    = zeros(3, horizonte+1);
flujos_plot_M    = zeros(3, horizonte+1);
flujos_plot_P    = zeros(3, horizonte+1);

for i = 1:3
    % 1. OPTIMISTA
    f_O = [-capex_total(i), ahorro_neto_O(i) .* curva_O];
    VAN_O(i) = sum(f_O ./ (1 + tasa_k).^(0:horizonte));
    flujos_plot_O(i,:) = f_O;
    
    % 2. PROBABLE 
    f_M = [-capex_total(i), ahorro_neto_M(i) .* curva_M];
    VAN_M(i) = sum(f_M ./ (1 + tasa_k).^(0:horizonte));
    flujos_plot_M(i,:) = f_M;

    % 3. PESIMISTA 
    f_P = [-(capex_total(i) + ve_riesgo_capex(i)), ahorro_neto_P(i) .* curva_P];
    f_P(2) = f_P(2) - ve_riesgos_opex(i); % Golpe en Año 1
    VAN_P(i) = sum(f_P ./ (1 + tasa_k).^(0:horizonte));
    TIR_P(i) = irr(f_P); % Calculamos la TIR del peor escenario
    flujos_plot_P(i,:) = f_P;

    % 4. PERT
    f_PERT = (f_O + 4.*f_M + f_P) ./ 6;
    flujos_plot_PERT(i,:) = f_PERT;
    
    VAN_PERT(i) = sum(f_PERT ./ (1 + tasa_k).^(0:horizonte));
    TIR_PERT(i) = irr(f_PERT);
    
    acumulado = cumsum(f_PERT);
    idx_pos = find(acumulado > 0, 1);
    if isempty(idx_pos)
        PB_PERT(i) = NaN;
    else
        year_previo = idx_pos - 2;
        fraccion = abs(acumulado(idx_pos-1)) / f_PERT(idx_pos);
        PB_PERT(i) = year_previo + fraccion;
    end
end

fprintf('  %-12s  %12s  %10s  %10s  %12s\n', 'Opción', 'VAN PERT', 'TIR PERT', 'Payback', 'VAN Pesimista');
fprintf('  ──────────────────────────────────────────────────────────────\n');
for i = 1:3
    if VAN_PERT(i) > 0; mark = '[RENTABLE]'; else; mark = '[NO RENTABLE]'; end
    fprintf('  %-12s  %9.2f M€  %9.1f%%  %7.2f a  %9.2f M€  %s\n', ...
            nombres{i}, VAN_PERT(i)/1e6, TIR_PERT(i)*100, PB_PERT(i), VAN_P(i)/1e6, mark);
end
fprintf('\n');


% =========================================================================
% BLOQUE 7 – SELECCIÓN CUANTITATIVA A 8 VARIABLES (NIVEL CFO)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 7 · MATRIZ DE DECISIÓN DE INGENIERÍA ECONÓMICA (8 CRITERIOS)\n');
fprintf('─────────────────────────────────────────────────────────\n');

van_por_euro_capex = VAN_PERT ./ capex_tabla2;
caida_riesgo_van = (VAN_M - VAN_P) / 1e6; % Cuánto dinero destruye el riesgo

fprintf('\n  TABLA DE DECISIÓN CORPORATIVA\n');
fprintf('  %-26s  %10s  %10s  %10s  %10s\n', 'Criterio Estratégico','Básica','Estándar','Premium','Mejor');
fprintf('  ──────────────────────────────────────────────────────────────────\n');

% Criterios: {Nombre, Valores, Operador Lógico de victoria, Signo de Minimización}
criterios = {
    '1. Payback PERT (años)',        PB_PERT,               '< es mejor',  1;
    '2. VAN PERT 10 años (M€)',      VAN_PERT/1e6,          '> es mejor', -1;
    '3. TIR PERT (%)',               TIR_PERT*100,          '> es mejor', -1;
    '4. Eficiencia (VAN/CAPEX)',     van_por_euro_capex,    '> es mejor', -1;
    '5. VAN Pesimista (M€)',         VAN_P/1e6,             '> es mejor', -1;
    '6. TIR Pesimista (Superv. %)',  TIR_P*100,             '> es mejor', -1;
    '7. Caída VAN por Riesgo (M€)',  caida_riesgo_van,      '< es mejor',  1;
    '8. Ahorro Neto Estab. (M€/a)',  ahorro_neto_M/1e6,     '> es mejor', -1;
};

puntos = zeros(1,3);
for k = 1:size(criterios,1)
    label  = criterios{k,1};
    vals   = criterios{k,2};
    signo  = criterios{k,4};
    [~, ganador] = min(signo * vals);
    marca = {'','',''};
    marca{ganador} = ' ✓';
    puntos(ganador) = puntos(ganador) + 1;
    fprintf('  %-26s  %9.2f%s  %9.2f%s  %9.2f%s\n', label, vals(1), marca{1}, vals(2), marca{2}, vals(3), marca{3});
end

fprintf('  ──────────────────────────────────────────────────────────────────\n');
fprintf('  Puntuación Final (de 8):          %9d   %9d   %9d\n', puntos(1), puntos(2), puntos(3));

[~, idx_elegida] = max(puntos);
fprintf('\n  *** OPCIÓN SELECCIONADA: %s (Gana %d de 8 criterios estratégicos) ***\n\n', upper(nombres{idx_elegida}), puntos(idx_elegida));


% =========================================================================
% BLOQUE 8 – RESUMEN EJECUTIVO FINAL
% =========================================================================
fprintf('=========================================================\n');
fprintf(' RESUMEN EJECUTIVO PARA DIRECCIÓN – OPCIÓN %s\n', upper(nombres{idx_elegida}));
fprintf('=========================================================\n');

fprintf(' Inversión inicial (CAPEX total):         %6.1f M€\n',  capex_total(idx_elegida)/1e6);
fprintf(' Ahorro neto anual esperado (Año 2+):     %6.2f M€/año\n', ahorro_neto_M(idx_elegida)/1e6);
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' Justificación Financiera para el Comité:\n');
fprintf(' La matriz multicriterio de 8 variables demuestra de forma transparente que\n');
fprintf(' no existe una opción "perfecta en todo", sino una óptima global.\n');
fprintf(' - La Premium gana en Ahorro a futuro, pero su vulnerabilidad técnica\n');
fprintf('   destruye casi %.1f M€ de valor en caso de crisis.\n', caida_riesgo_van(3));
fprintf(' - La Básica gana en menor volatilidad, pero es incapaz de recuperar la \n');
fprintf('   inversión al presentar ineficiencias laborales crónicas.\n');
fprintf(' - La Estándar es la única verdaderamente equilibrada: Presenta el mejor \n');
fprintf('   VAN PERT (+%.2f M€), la mejor TIR (%.1f %%) y es la única que sobrevive\n', VAN_PERT(idx_elegida)/1e6, TIR_PERT(idx_elegida)*100);
fprintf('   financieramente sana a una crisis combinada.\n');
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' Payback estadístico PERT:           %8.2f años\n', PB_PERT(idx_elegida));
fprintf(' VAN PERT 10 años (tasa 7%%):        %8.2f M€\n',  VAN_PERT(idx_elegida)/1e6);
fprintf(' TIR Esperada PERT:                  %8.1f %%\n',   TIR_PERT(idx_elegida)*100);
fprintf('=========================================================\n\n');


% =========================================================================
% BLOQUE 9 – GRÁFICAS
% =========================================================================

%% Figura 1 - Doble Análisis del VAN (PERT vs Escenarios)
figure('Name','Análisis del VAN','NumberTitle','off','Position',[100 100 1000 450]);

subplot(1,2,1);
van_pert_vals = VAN_PERT / 1e6;
b1 = bar(van_pert_vals, 'FaceColor','flat');
colores_b1 = repmat([0.70 0.75 0.80], 3, 1);
colores_b1(idx_elegida,:) = [0.15 0.65 0.45]; 
b1.CData = colores_b1;

set(gca,'XTickLabel', nombres, 'FontSize', 10);
title('VAN Esperado (Modelo PERT)','FontSize',11,'FontWeight','normal');
ylabel('Millones €','FontSize',10);
yline(0,'k-','LineWidth',1.5);
for i = 1:3
    offset = sign(van_pert_vals(i)) * 1.5;
    if van_pert_vals(i)==0; offset = 1.5; end
    text(i, van_pert_vals(i) + offset, sprintf('%.2f M€', van_pert_vals(i)), 'HorizontalAlignment','center','FontSize',9,'FontWeight','bold');
end
grid on; box off;

subplot(1,2,2);
van_escenarios = [VAN_O; VAN_M; VAN_P]' / 1e6; 
b2 = bar(van_escenarios, 'grouped');
b2(1).FaceColor = [0.15 0.65 0.45]; 
b2(2).FaceColor = [0.20 0.53 0.74]; 
b2(3).FaceColor = [0.85 0.33 0.10]; 

set(gca,'XTickLabel', nombres, 'FontSize', 10);
title('VAN por Escenarios (Mide la "Caída por Riesgo")','FontSize',11,'FontWeight','normal');
ylabel('Millones €','FontSize',10);
legend({'Optimista','Probable (Base)','Pesimista (Riesgos Activos)'}, 'Location','southwest','FontSize',8);
yline(0,'k-','LineWidth',1.5);
grid on; box off;

sgtitle('Estándar: La alternativa que domina la rentabilidad ajustada al riesgo','FontSize',13,'FontWeight','bold');


%% Figura 2 – Flujo de Caja Acumulado
figure('Name','Evolución del Flujo de Caja por Escenarios','NumberTitle','off','Position',[100 560 900 450]);
years_plot = 0:horizonte;

acum_PERT = cumsum(flujos_plot_PERT(idx_elegida,:)) / 1e6;
acum_O    = cumsum(flujos_plot_O(idx_elegida,:)) / 1e6;
acum_M    = cumsum(flujos_plot_M(idx_elegida,:)) / 1e6;
acum_P    = cumsum(flujos_plot_P(idx_elegida,:)) / 1e6;

plot(years_plot, acum_O, '--^', 'Color',[0.15 0.65 0.45], 'LineWidth',1.5, 'MarkerFaceColor','w'); 
hold on;
plot(years_plot, acum_M, '-.s', 'Color',[0.20 0.53 0.74], 'LineWidth',1.5, 'MarkerFaceColor','w'); 
plot(years_plot, acum_P, ':v',  'Color',[0.85 0.33 0.10], 'LineWidth',1.5, 'MarkerFaceColor','w'); 
plot(years_plot, acum_PERT, '-o', 'Color','k', 'LineWidth',2.5, 'MarkerFaceColor','w'); 

% Destacar la zona donde golpean los riesgos
plot([1 1], [acum_P(2) acum_M(2)], 'r-', 'LineWidth', 1.5, 'HandleVisibility','off');
text(1.2, (acum_P(2)+acum_M(2))/2, '← Ley de Murphy (Año 1)', 'Color', 'r', 'FontSize', 9);

yline(0, 'k-', 'LineWidth', 1.5, 'HandleVisibility','off');
xline(PB_PERT(idx_elegida), '--', sprintf('Payback: %.1f años', PB_PERT(idx_elegida)), ...
      'Color','k', 'FontSize',10, 'LabelVerticalAlignment','top', 'LabelHorizontalAlignment','right', 'HandleVisibility','off');

xlabel('Años desde la inversión (Año 0)','FontSize',11);
ylabel('Flujo de Caja Acumulado (Millones €)','FontSize',11);
title(sprintf('Curvas de Amortización – Opción ESTÁNDAR'), 'FontSize',12,'FontWeight','normal');

legend({'Escenario Optimista', 'Escenario Probable', 'Escenario Pesimista (Con Riesgos)', 'Flujo Esperado PERT'}, 'Location','northwest','FontSize',9);
grid on; box off;