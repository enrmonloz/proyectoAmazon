% =========================================================================
% COMPARACIÓN DE ESTRATEGIAS: ABC INDIVIDUAL vs ABC GLOBAL (3D)
% =========================================================================
clear; clc; close all;

%% 1. PARÁMETROS DE ENTRADA (Misma configuración física)
num_filas = 50; 
num_cols = 100;
num_plantas = 3;
est_por_planta = num_filas * num_cols; % 5.000
total_estanterias = est_por_planta * num_plantas; % 15.000

puertas = [1, 50; 50, 10; 50, 90];
P = [0.50, 0.25, 0.25]; 

% Penalización vertical en celdas (basado en 18 metros a 1.2 m/s)
penalizacion_celdas = 12; 
dist_planta = [penalizacion_celdas, 2*penalizacion_celdas, 3*penalizacion_celdas];

% Inventario y Frecuencia de Movimientos
pct_A = 0.15;   movimientos_A = 0.80; % 80% del trabajo diario
pct_B = 0.15;   movimientos_B = 0.15; % 15% del trabajo diario
pct_C = 0.70;   movimientos_C = 0.05; % 5% del trabajo diario

%% 2. CÁLCULO DE LA MATRIZ f GLOBAL
matriz_f = zeros(num_filas, num_cols, num_plantas);
num_puertas = size(puertas, 1);

for p = 1:num_plantas
    for r = 1:num_filas
        for c = 1:num_cols
            f_val = 0;
            for d = 1:num_puertas
                dist_horizontal_celdas = abs(r - puertas(d, 1)) + abs(c - puertas(d, 2));
                f_val = f_val + P(d) * (dist_horizontal_celdas + dist_planta(p));
            end
            matriz_f(r, c, p) = f_val;
        end
    end
end

%% 3. ESTRATEGIA 1: ABC INDIVIDUAL (Por planta separada)
% Cantidades a repartir EN CADA PLANTA
num_A_ind = round(est_por_planta * pct_A); % 750
num_B_ind = round(est_por_planta * pct_B); % 750
num_C_ind = est_por_planta - num_A_ind - num_B_ind; % 3500

coste_total_ind = 0;

for p = 1:num_plantas
    % Extraemos los valores f solo de esta planta y los ordenamos
    f_planta = matriz_f(:, :, p);
    f_ordenado_planta = sort(f_planta(:));
    
    % Asignamos pesos y calculamos coste
    suma_f_A_ind = sum(f_ordenado_planta(1 : num_A_ind));
    suma_f_B_ind = sum(f_ordenado_planta(num_A_ind + 1 : num_A_ind + num_B_ind));
    suma_f_C_ind = sum(f_ordenado_planta(num_A_ind + num_B_ind + 1 : end));
    
    % El coste es la suma de f ponderada por el peso por celda de esa categoría
    peso_celda_A = movimientos_A / (num_A_ind * 3); % Repartido en 3 plantas
    peso_celda_B = movimientos_B / (num_B_ind * 3);
    peso_celda_C = movimientos_C / (num_C_ind * 3);
    
    coste_total_ind = coste_total_ind + (suma_f_A_ind * peso_celda_A) + ...
                                        (suma_f_B_ind * peso_celda_B) + ...
                                        (suma_f_C_ind * peso_celda_C);
end

%% 4. ESTRATEGIA 2: ABC GLOBAL (Teniendo en cuenta las 3 plantas)
% Cantidades a repartir EN TOTAL
num_A_glob = round(total_estanterias * pct_A); % 2250
num_B_glob = round(total_estanterias * pct_B); % 2250
num_C_glob = total_estanterias - num_A_glob - num_B_glob; % 10500

% Ordenamos TODAS las celdas del edificio juntas
f_ordenado_glob = sort(matriz_f(:));

suma_f_A_glob = sum(f_ordenado_glob(1 : num_A_glob));
suma_f_B_glob = sum(f_ordenado_glob(num_A_glob + 1 : num_A_glob + num_B_glob));
suma_f_C_glob = sum(f_ordenado_glob(num_A_glob + num_B_glob + 1 : end));

% Coste Global
peso_celda_A_g = movimientos_A / num_A_glob;
peso_celda_B_g = movimientos_B / num_B_glob;
peso_celda_C_g = movimientos_C / num_C_glob;

coste_total_glob = (suma_f_A_glob * peso_celda_A_g) + ...
                   (suma_f_B_glob * peso_celda_B_g) + ...
                   (suma_f_C_glob * peso_celda_C_g);

%% 5. ANÁLISIS DE RESULTADOS Y GRÁFICA
ahorro_absoluto = coste_total_ind - coste_total_glob;
ahorro_porcentaje = (ahorro_absoluto / coste_total_ind) * 100;

% Imprimir Resultados
fprintf('======================================================\n');
fprintf('  COMPARATIVA DE ESTRATEGIAS DE ALMACENAMIENTO\n');
fprintf('======================================================\n\n');

fprintf('ESTRATEGIA 1: ABC por Planta Individual\n');
fprintf('   El producto A se reparte obligatoriamente en P1, P2 y P3.\n');
fprintf('   Índice de Coste Logístico Diario: %.2f\n\n', coste_total_ind);

fprintf('ESTRATEGIA 2: ABC Global Optimizado 3D\n');
fprintf('   El producto A se concentra en las mejores zonas de la P1.\n');
fprintf('   Índice de Coste Logístico Diario: %.2f\n\n', coste_total_glob);

fprintf('======================================================\n');
fprintf('CONCLUSIÓN:\n');
fprintf('La Estrategia Global es un %.2f%% más eficiente.\n', ahorro_porcentaje);
fprintf('======================================================\n');

% Gráfica de Barras para visualización
figure('Name', 'Comparativa de Eficiencia', 'NumberTitle', 'off', 'Position', [200, 200, 600, 400]);
b = bar([1, 2], [coste_total_ind, coste_total_glob], 0.5);
b.FaceColor = 'flat';
b.CData(1,:) = [0.8 0.2 0.2]; % Rojo para la estrategia mala
b.CData(2,:) = [0.2 0.8 0.2]; % Verde para la estrategia buena

set(gca, 'XTickLabel', {'Estrategia 1: ABC por Planta', 'Estrategia 2: ABC Global 3D'});
ylabel('Coste Logístico Diario (f \times Movimientos)');
title(sprintf('Ahorro del %.2f%% en desplazamientos', ahorro_porcentaje));
grid on;