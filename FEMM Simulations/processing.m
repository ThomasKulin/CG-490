%load f and z variables

%Variable Declaration
m = 0.018;  % mass in Kg
v0 = 0;  % initial velocity in m/s

plot(z, f, '-*')
grid on
title('Force vs. Distance')
xlabel('Distance [cm]')
ylabel('Force [N]')

%taking the integral of force over distance gives the total work in
%Kg*m^2/s^2 which is equivalent to change in kinetic energy 
% W = KEf - KEi
wt = cumtrapz(z,f);
vt = sqrt(2*wt/m);
w = trapz(z,f);
v = sqrt(2*w/m);

