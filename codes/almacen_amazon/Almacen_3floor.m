% =========================================================================
% OPTIMIZACIÓN DE LAYOUT 3D - MÉTODO f (CON CÁLCULO FÍSICO DE CINTAS)
% =========================================================================
clear; clc; close all;

%% 1. VARIABLES AJUSTABLES (PARÁMETROS DE ENTRADA)
% -------------------------------------------------------------------------
% Dimensiones de la cuadrícula por planta
num_filas = 50; 
num_cols = 100;
num_plantas = 3;
total_estanterias = num_filas * num_cols * num_plantas; % 15.000

% Posiciones de las puertas o puntos de E/S en la planta baja [Fila, Columna]
puertas = [
    1, 50;      % Puerta 1 (Salida): Centro de la pared superior
    50, 10;     % Puerta 2 (Entrada): Esquina inferior izquierda
    50, 50      % Puerta 3 (Salida): Esquina inferior derecha
];

% Porcentaje de uso de cada puerta (Pi)
P = [0.50, 0.25, 0.25]; 

% -------------------------------------------------------------------------
% PARÁMETROS FÍSICOS Y DE CINEMÁTICA (NUEVO)
% -------------------------------------------------------------------------
tamano_celda = 1.5;        % Metros (Lado de cada cuadrícula)
v_cinta = 1.2;             % m/s (Velocidad de la cinta transportadora)
tiempo_T = 15;             % Segundos (Tiempo en subir de P0 a P1)

% Distancia real en metros que recorre el producto en la cinta
dist_vertical_metros = v_cinta * tiempo_T; 

% Convertimos la distancia a "unidades de celda" para poder sumarlo a Dik
penalizacion_celdas = dist_vertical_metros / tamano_celda;

% Vector de distancias a sumar por cada planta (P1, P2, P3)
dist_planta = [penalizacion_celdas, 2*penalizacion_celdas, 3*penalizacion_celdas];

% Porcentajes de inventario ABC
pct_A = 0.15;   
pct_B = 0.15;   
pct_C = 0.70;   

%% 2. CÁLCULO DEL ÍNDICE f GLOBAL (3D)
% -------------------------------------------------------------------------
matriz_f = zeros(num_filas, num_cols, num_plantas);
num_puertas = size(puertas, 1);

for p = 1:num_plantas
    for r = 1:num_filas
        for c = 1:num_cols
            f_val = 0;
            for d = 1:num_puertas
                % Distancia horizontal (Manhattan) en celdas
                dist_horizontal_celdas = abs(r - puertas(d, 1)) + abs(c - puertas(d, 2));
                
                % Fórmula corregida: Pi * (Dik_horizontal + Distancia_Vertical)
                f_val = f_val + P(d) * (dist_horizontal_celdas + dist_planta(p));
            end
            matriz_f(r, c, p) = f_val;
        end
    end
end

%% 3. ASIGNACIÓN ABC GLOBAL
% -------------------------------------------------------------------------
num_A = round(total_estanterias * pct_A);
num_B = round(total_estanterias * pct_B);
num_C = total_estanterias - num_A - num_B; 

[~, indices_ordenados] = sort(matriz_f(:));
matriz_ABC = zeros(num_filas, num_cols, num_plantas);

matriz_ABC(indices_ordenados(1:num_A)) = 1;                           % Zona A
matriz_ABC(indices_ordenados(num_A + 1 : num_A + num_B)) = 2;         % Zona B
matriz_ABC(indices_ordenados(num_A + num_B + 1 : end)) = 3;           % Zona C

%% 4. FIGURA 1: ZONIFICACIÓN ABC POR PLANTAS
% -------------------------------------------------------------------------
figure('Name', 'Zonificación ABC en 3 Plantas', 'NumberTitle', 'off', 'Position', [100, 100, 800, 900]);

for p = 1:num_plantas
    subplot(3, 1, p);
    imagesc(matriz_ABC(:, :, p), [1 3]);
    colormap(gca, [0.2 0.8 0.2; 1 0.8 0; 0.8 0.2 0.2]); 
    
    colorbar('Ticks', [1.33, 2, 2.66], 'TickLabels', {'A (15%)', 'B (15%)', 'C (70%)'});
    % Mostramos el dato físico en el título para justificar el diseño
    title(sprintf('PLANTA %d (Dist. Vertical Añadida: %.1f m / %.1f celdas)', p, dist_vertical_metros*p, dist_planta(p)));
    ylabel('Filas');
    axis equal tight;
    hold on;
    
    for d = 1:num_puertas
        plot(puertas(d, 2), puertas(d, 1), 'kx', 'MarkerSize', 10, 'LineWidth', 2);
    end
    hold off;
end
xlabel('Columnas');

%% 5. FIGURA 2: MAPA DE VALORES f POR PLANTAS
% -------------------------------------------------------------------------
figure('Name', 'Mapa de Valores f (3D)', 'NumberTitle', 'off', 'Position', [150, 100, 800, 900]);

f_min = min(matriz_f(:));
f_max = max(matriz_f(:));

for p = 1:num_plantas
    subplot(3, 1, p);
    imagesc(matriz_f(:, :, p), [f_min, f_max]); 
    colormap(gca, jet); 
    
    colorbar;
    title(sprintf('Valores f (Equivalente en Celdas) - PLANTA %d', p));
    ylabel('Filas');
    axis equal tight;
    hold on;
    
    for d = 1:num_puertas
        plot(puertas(d, 2), puertas(d, 1), 'wx', 'MarkerSize', 10, 'LineWidth', 2);
    end
    hold off;
end
xlabel('Columnas');