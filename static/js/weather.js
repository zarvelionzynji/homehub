/**
 * Weather Widget for Home Hub
 * Uses Open-Meteo API to display current weather conditions
 */
(function(){
    'use strict';

    // Load i18n strings from injected JSON
    var t = {};
    try {
        var el = document.getElementById('weatherI18n');
        if (el) t = JSON.parse(el.textContent || '{}');
    } catch(e) {}
    function _(k) { return t[k] || k; }

    // Weather code mapping (WMO Weather interpretation codes)
    var weatherCodes = {
        0: { desc: _('Clear'), icon: 'fa-sun', color: 'text-yellow-400' },
        1: { desc: _('Mainly Clear'), icon: 'fa-cloud-sun', color: 'text-yellow-400' },
        2: { desc: _('Partly Cloudy'), icon: 'fa-cloud', color: 'text-gray-400' },
        3: { desc: _('Overcast'), icon: 'fa-cloud', color: 'text-gray-500' },
        45: { desc: _('Fog'), icon: 'fa-smog', color: 'text-gray-400' },
        48: { desc: _('Freezing Fog'), icon: 'fa-smog', color: 'text-cyan-200' },
        51: { desc: _('Light Drizzle'), icon: 'fa-cloud-rain', color: 'text-blue-400' },
        53: { desc: _('Drizzle'), icon: 'fa-cloud-rain', color: 'text-blue-500' },
        55: { desc: _('Heavy Drizzle'), icon: 'fa-cloud-showers-heavy', color: 'text-blue-600' },
        61: { desc: _('Light Rain'), icon: 'fa-cloud-rain', color: 'text-blue-400' },
        63: { desc: _('Rain'), icon: 'fa-cloud-rain', color: 'text-blue-500' },
        65: { desc: _('Heavy Rain'), icon: 'fa-cloud-showers-heavy', color: 'text-blue-600' },
        71: { desc: _('Light Snow'), icon: 'fa-snowflake', color: 'text-cyan-300' },
        73: { desc: _('Snow'), icon: 'fa-snowflake', color: 'text-cyan-400' },
        75: { desc: _('Heavy Snow'), icon: 'fa-snowflake', color: 'text-cyan-500' },
        77: { desc: _('Snow Grains'), icon: 'fa-snowflake', color: 'text-cyan-400' },
        80: { desc: _('Light Showers'), icon: 'fa-cloud-sun-rain', color: 'text-blue-400' },
        81: { desc: _('Showers'), icon: 'fa-cloud-showers-heavy', color: 'text-blue-500' },
        82: { desc: _('Heavy Showers'), icon: 'fa-cloud-showers-heavy', color: 'text-blue-600' },
        85: { desc: _('Snow Showers'), icon: 'fa-snowflake', color: 'text-cyan-300' },
        86: { desc: _('Heavy Snow Showers'), icon: 'fa-snowflake', color: 'text-cyan-400' },
        95: { desc: _('Thunderstorm'), icon: 'fa-bolt', color: 'text-yellow-500' },
        96: { desc: _('Thunderstorm + Hail'), icon: 'fa-cloud-bolt', color: 'text-yellow-600' },
        99: { desc: _('Thunderstorm + Hail'), icon: 'fa-cloud-bolt', color: 'text-yellow-600' }
    };

    function getWeatherIcon(code) {
        return weatherCodes[code] || { desc: _('Unknown'), icon: 'fa-question', color: 'text-gray-500' };
    }

    function displayError(container, message) {
        container.innerHTML = '<div class="text-center text-red-500 py-4"><i class="fa-solid fa-exclamation-triangle text-2xl"></i><p class="mt-2">' + message + '</p></div>';
    }

    var TTL_MS = 15 * 60 * 1000;

    function displayWeather(container, data, units, cfg) {
        var current = data.current;
        if (!current) { displayError(container, _('Invalid weather data received')); return; }

        var temp = current.temperature_2m;
        var weatherCode = current.weather_code || 0;
        var windSpeed = current.wind_speed_10m || 0;
        var windGust = current.wind_gusts_10m || null;
        var windDir = current.wind_direction_10m;
        var humidity = current.relative_humidity_2m ?? null;
        var feelsLike = current.apparent_temperature ?? null;
        var precipitation = current.precipitation ?? null;
        var rain = current.rain ?? null;
        var weather = getWeatherIcon(weatherCode);
        var tempUnit = units === 'imperial' ? '°F' : '°C';
        var speedUnit = units === 'imperial' ? 'mph' : 'km/h';

        if (current.is_day === 0 && [0, 1].includes(weatherCode)) {
            weather = { desc: _('Clear'), icon: 'fa-moon', color: 'text-indigo-300' };
        }

        var precipLabel = ((rain !== null && rain !== undefined ? rain : precipitation) || 0) > 0
            ? (rain ?? precipitation).toFixed(1) + ' mm'
            : _('No rain');
        var feelsLikeText = typeof feelsLike === 'number' ? Math.round(feelsLike) + tempUnit : '—';
        var humidityText = typeof humidity === 'number' ? Math.round(humidity) + '%' : '—';

        function degToCompass(deg) {
            if (typeof deg !== 'number' || isNaN(deg)) return '';
            return ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'][Math.round(deg / 22.5) % 16];
        }
        var windDirText = degToCompass(windDir);
        var windLine = Math.round(windSpeed) + ' ' + speedUnit + ' ' + windDirText;
        var gustLine = (windGust !== null && windGust !== undefined) ? Math.round(windGust) + ' ' + speedUnit : '—';

        var dailyHtml = '';
        var daily = data.daily || null;
        if (cfg && cfg.view === 'detailed' && daily) {
            var fmtTime = function(s) {
                try {
                    var d = new Date(s);
                    var opts = { hour: '2-digit', minute: '2-digit' };
                    if (cfg.timezone) opts.timeZone = cfg.timezone;
                    return d.toLocaleTimeString(undefined, opts);
                } catch(e) { return String(s).split('T')[1] || String(s); }
            };
            var uv = daily.uv_index_max?.[0] ?? '—';
            var rainProb = daily.precipitation_probability_max?.[0] ?? '—';
            var tMax = daily.temperature_2m_max?.[0];
            var tMin = daily.temperature_2m_min?.[0];
            var sunrise = daily.sunrise?.[0] ? fmtTime(daily.sunrise[0]) : '—';
            var sunset = daily.sunset?.[0] ? fmtTime(daily.sunset[0]) : '—';

            dailyHtml = '<div class="pt-3 mt-3 border-t border-opacity-20 border-current">'
                + '<div class="flex items-center justify-between mb-2">'
                + '<div class="text-base font-semibold">' + _("Today's Forecast") + '</div>'
                + '<div class="text-sm opacity-80 flex items-center gap-2"><i class="fa-solid fa-arrow-up-long text-red-500"></i> ' + _('H') + ': <span class="font-semibold opacity-100">' + (tMax!=null?Math.round(tMax)+tempUnit:'—') + '</span> <i class="fa-solid fa-arrow-down-long text-blue-500 ml-3"></i> ' + _('L') + ': <span class="font-semibold opacity-100">' + (tMin!=null?Math.round(tMin)+tempUnit:'—') + '</span></div>'
                + '</div>'
                + '<div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm opacity-80">'
                + '<div class="flex items-center gap-2"><i class="fa-solid fa-sun text-amber-500"></i><span>' + _('Sunrise') + ': <span class="font-semibold opacity-100">' + sunrise + '</span></span></div>'
                + '<div class="flex items-center gap-2"><i class="fa-solid fa-moon text-indigo-400"></i><span>' + _('Sunset') + ': <span class="font-semibold opacity-100">' + sunset + '</span></span></div>'
                + '<div class="flex items-center gap-2"><i class="fa-solid fa-sun text-yellow-500"></i><span>' + _('UV Index') + ': <span class="font-semibold opacity-100">' + (uv!=null?uv:'—') + '</span></span></div>'
                + '<div class="flex items-center gap-2"><i class="fa-solid fa-cloud-rain text-blue-500"></i><span>' + _('Rain') + ': <span class="font-semibold opacity-100">' + (rainProb!=null?rainProb+'%':'—') + '</span></span></div>'
                + '</div></div>';
        }

        container.innerHTML = '<div class="flex flex-col md:flex-row items-center md:items-start justify-between gap-4 md:gap-6">'
            + '<div class="flex items-center md:items-start gap-3 md:gap-4">'
            + '<i class="fa-solid ' + weather.icon + ' ' + weather.color + ' text-5xl md:text-6xl"></i>'
            + '<div><div class="text-4xl md:text-5xl font-bold">' + Math.round(temp) + tempUnit + '</div>'
            + '<div class="opacity-70 text-lg">' + weather.desc + '</div></div></div>'
            + '<div class="grid grid-cols-2 gap-x-6 gap-y-2 w-full md:w-auto text-sm md:text-base opacity-90">'
            + '<div class="flex items-center gap-2"><i class="fa-solid fa-temperature-half opacity-60"></i><span>' + _('Feels like') + ': <span class="font-semibold opacity-100">' + feelsLikeText + '</span></span></div>'
            + '<div class="flex items-center gap-2"><i class="fa-solid fa-wind opacity-60"></i><span>' + _('Wind') + ': <span class="font-semibold opacity-100">' + windLine + '</span></span></div>'
            + '<div class="flex items-center gap-2"><i class="fa-solid fa-wind opacity-60"></i><span>' + _('Gusts') + ': <span class="font-semibold opacity-100">' + gustLine + '</span></span></div>'
            + '<div class="flex items-center gap-2"><i class="fa-solid fa-droplet opacity-60"></i><span>' + _('Humidity') + ': <span class="font-semibold opacity-100">' + humidityText + '</span></span></div>'
            + '<div class="flex items-center gap-2"><i class="fa-solid fa-cloud-rain opacity-60"></i><span>' + _('Rain') + ': <span class="font-semibold opacity-100">' + precipLabel + '</span></span></div>'
            + '</div></div>'
            + dailyHtml;

        if (current.time) {
            try {
                var dt = new Date(current.time);
                var diffMin = Math.floor((Date.now() - dt.getTime()) / 60000);
                var relativeTime = '';
                if (diffMin < 1) relativeTime = _('just now');
                else if (diffMin === 1) relativeTime = _('1 minute ago');
                else if (diffMin < 60) relativeTime = _('%(n)d minutes ago').replace('%(n)d', diffMin);
                else if (diffMin < 120) relativeTime = _('1 hour ago');
                else relativeTime = _('%(n)d hours ago').replace('%(n)d', Math.floor(diffMin/60));
                var opts = { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' };
                if (cfg && cfg.timezone) opts.timeZone = cfg.timezone;
                var absTime = dt.toLocaleString(undefined, opts);
                container.insertAdjacentHTML('beforeend', '<div class="text-[11px] opacity-60 mt-3 md:mt-4 text-right">' + _('Last updated') + ': ' + absTime + ' (' + relativeTime + ')</div>');
            } catch(e) {
                container.insertAdjacentHTML('beforeend', '<div class="text-[11px] opacity-60 mt-3 md:mt-4 text-right">' + _('Last updated') + ': ' + String(current.time).replace('T',' ') + '</div>');
            }
        }
    }

    var CACHE_VERSION = 'v2';

    async function fetchWeather(lat, lon, config, cache, retryCount) {
        if (retryCount === undefined) retryCount = 0;
        var now = Date.now();
        var latKey = lat.toFixed(3);
        var lonKey = lon.toFixed(3);
        var tzKey = config.timezone ? config.timezone : 'auto';
        var viewKey = config.view || 'compact';
        var unitsKey = (config.units || 'metric');
        var storageKey = 'weatherCache:' + CACHE_VERSION + ':' + latKey + ',' + lonKey + ':' + unitsKey + ':' + viewKey + ':' + tzKey;

        try {
            var allKeys = Object.keys(localStorage);
            allKeys.forEach(function(k) {
                if (k.startsWith('weatherCache:') && !k.startsWith('weatherCache:' + CACHE_VERSION + ':')) {
                    localStorage.removeItem(k);
                }
            });
        } catch(_) {}

        try {
            var raw = localStorage.getItem(storageKey);
            if (raw) {
                var obj = JSON.parse(raw);
                if (obj && obj.data && obj.data.current && obj.data.current.time) {
                    var apiTime = new Date(obj.data.current.time).getTime();
                    var ageMs = now - apiTime;
                    if (ageMs < TTL_MS && ageMs >= 0) {
                        cache.data = obj.data;
                        cache.time = apiTime;
                        return obj.data;
                    }
                }
            }
        } catch(_) {}

        var params = new URLSearchParams({
            latitude: lat,
            longitude: lon,
            current: 'is_day,apparent_temperature,relative_humidity_2m,temperature_2m,precipitation,rain,weather_code,wind_gusts_10m,wind_speed_10m,wind_direction_10m',
            temperature_unit: config.units === 'imperial' ? 'fahrenheit' : 'celsius',
            windspeed_unit: config.units === 'imperial' ? 'mph' : 'kmh',
            precipitation_unit: 'mm'
        });

        if ((config.view || 'compact') === 'detailed') {
            params.append('daily', 'sunrise,sunset,uv_index_max,precipitation_probability_max,temperature_2m_max,temperature_2m_min');
        }
        params.append('timezone', config.timezone ? config.timezone : 'auto');

        try {
            var response = await fetch('/api/weather?' + params);
            if (!response.ok) throw new Error('Weather API returned ' + response.status);
            var data = await response.json();
            var apiTime = data.current && data.current.time ? new Date(data.current.time).getTime() : now;
            cache.data = data;
            cache.time = apiTime;
            try { localStorage.setItem(storageKey, JSON.stringify({ data: data })); } catch(_) {}
            return data;
        } catch (error) {
            if (retryCount < 2) {
                var delay = Math.pow(2, retryCount) * 1000;
                await new Promise(function(r) { setTimeout(r, delay); });
                return fetchWeather(lat, lon, config, cache, retryCount + 1);
            }
            throw error;
        }
    }

    window.initWeatherWidget = function(config) {
        var weatherContent = document.getElementById('weatherContent');
        var weatherLocation = document.getElementById('weatherLocation');
        if (!weatherContent || !weatherLocation) { console.warn('Weather widget elements not found'); return; }

        config = config || {};
        config.units = config.units || 'metric';
        config.view = config.view || 'compact';
        var cache = { data: null, time: null };

        async function initWithCoords(lat, lon) {
            if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
                // Build error with translated args
                var msg = _('Invalid coordinates') + '. Latitude must be -90 to 90, longitude -180 to 180.';
                displayError(weatherContent, msg);
                return;
            }
            if (config.label) weatherLocation.textContent = config.label;

            var loadAndRender = async function() {
                try {
                    var data = await fetchWeather(lat, lon, config, cache);
                    displayWeather(weatherContent, data, config.units, config);
                    if (!config.label && data && data.timezone) weatherLocation.textContent = '';
                } catch (error) {
                    console.error('Weather fetch error:', error);
                    displayError(weatherContent, _('Failed to load weather data'));
                }
            };

            await loadAndRender();
            var now = Date.now();
            var age = cache.time ? (now - cache.time) : TTL_MS;
            var firstDelay = Math.max(1000, TTL_MS - age);

            if (window.__weatherRefreshTimer) clearInterval(window.__weatherRefreshTimer);
            if (window.__weatherRefreshKickoff) clearTimeout(window.__weatherRefreshKickoff);

            if (age < TTL_MS) {
                window.__weatherRefreshKickoff = setTimeout(function() {
                    loadAndRender();
                    window.__weatherRefreshTimer = setInterval(loadAndRender, TTL_MS);
                }, firstDelay);
            }
        }

        if (config.latitude && config.longitude) {
            initWithCoords(parseFloat(config.latitude), parseFloat(config.longitude));
        } else if ('geolocation' in navigator && window.isSecureContext) {
            navigator.geolocation.getCurrentPosition(
                function(position) { initWithCoords(position.coords.latitude, position.coords.longitude); },
                function(error) {
                    console.error('Geolocation error:', error);
                    displayError(weatherContent, _('Unable to get your location') + '. ' + _('Please configure coordinates in config.yml'));
                }
            );
        } else {
            displayError(weatherContent, _('Unable to get your location') + '.');
        }
    };
})();
