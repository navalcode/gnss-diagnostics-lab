/* Original spherical distance kernel. MIT, Manuel Naval, 2026. */
#include <math.h>
#include <stddef.h>

int gnss_distance_deg(double lat_a, double lon_a, double lat_b, double lon_b, double *out_m) {
    if (out_m == NULL || !isfinite(lat_a) || !isfinite(lon_a) || !isfinite(lat_b) || !isfinite(lon_b)
        || lat_a < -90 || lat_a > 90 || lat_b < -90 || lat_b > 90
        || lon_a < -180 || lon_a > 180 || lon_b < -180 || lon_b > 180) return 1;
    const double radians = 3.14159265358979323846 / 180.0;
    const double a = lat_a * radians, b = lat_b * radians;
    const double x = sin((b-a)/2), y = sin((lon_b-lon_a)*radians/2);
    double h = x*x + cos(a)*cos(b)*y*y;
    h = fmin(1.0, fmax(0.0, h));
    *out_m = 2.0 * 6371000.0 * asin(sqrt(h));
    return 0;
}
