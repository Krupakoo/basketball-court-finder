import React, { useState, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import axios from "axios";
import "leaflet/dist/leaflet.css";
import "./App.css";


const createRotatedUserIcon = (heading) => {
  return L.divIcon({
    className: "user-heading-marker",
    html: `
      <div style="position: relative; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;">
        <div style="
          transform: rotate(${heading || 0}deg);
          transition: transform 0.15s ease-out;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #ffffff;
          border-radius: 50%;
          box-shadow: 0 0 14px rgba(37, 99, 235, 0.7);
        ">
          <svg viewBox="0 0 32 32" width="20" height="20">
            <polygon points="16,4 24,24 16,19 8,24" fill="#2563eb" stroke="#1d4ed8" stroke-width="1.5" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -22],
  });
};

const createCourtMarkerIcon = (court) => {
  const isPending = court.status === "pending";
  const isFeatured = !isPending && ((court.hoops_count >= 2 && court.has_lighting) || court.active_players_count > 0);

  if (isPending) {
    return L.divIcon({
      className: "custom-court-marker",
      html: `
        <div class="marker-pin-wrapper">
          <div class="marker-bubble pending">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -16],
    });
  }

  if (isFeatured) {
    return L.divIcon({
      className: "custom-court-marker",
      html: `
        <div class="marker-pin-wrapper featured-wrapper">
          <span class="marker-label">${court.name}</span>
          <div class="marker-bubble featured">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="9"/>
              <path d="M12 3v18M3 12h18"/>
            </svg>
          </div>
        </div>
      `,
      iconSize: [160, 56],
      iconAnchor: [80, 40], 
      popupAnchor: [0, -42],
    });
  }

  return L.divIcon({
    className: "custom-court-marker",
    html: `
      <div class="marker-pin-wrapper">
        <div class="marker-bubble standard">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="#e2e8f0" stroke-width="2">
            <circle cx="12" cy="12" r="9"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -15],
  });
};

function MapClickHandler({ onMapClick }) {
  useMapEvents({ click: (e) => onMapClick(e.latlng) });
  return null;
}

function RecenterMap({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    if (lat && lng) map.setView([lat, lng], 13);
  }, [lat, lng, map]);
  return null;
}

export default function App() {
  const [userLocation, setUserLocation] = useState({ lat: 50.0004, lng: 20.6053 });
  const [userHeading, setUserHeading] = useState(0);
  const [courts, setCourts] = useState([]);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token") || "");


  const [filterLighting, setFilterLighting] = useState(false);
  const [filterRim, setFilterRim] = useState("");


  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" });

  const [isAddCourtOpen, setIsAddCourtOpen] = useState(false);
  const [newCourtPos, setNewCourtPos] = useState(null);
  const [courtForm, setCourtForm] = useState({
    name: "",
    surface: "asfalt",
    hoops_count: 2,
    has_lighting: false,
    backboard_type: "stal/krata",
    rim_type: "standard_rigid",
    net_type: "lancuchowa",
  });
  const [courtImages, setCourtImages] = useState([]);

  const [isLeaderboardOpen, setIsLeaderboardOpen] = useState(false);
  const [leaderboardData, setLeaderboardData] = useState([]);

  const [activeCourtForMatches, setActiveCourtForMatches] = useState(null);
  const [courtMatches, setCourtMatches] = useState([]);
  const [newMatchForm, setNewMatchForm] = useState({ scheduled_time: "", max_players: 6 });

  const [notification, setNotification] = useState("");

  const showNotify = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(""), 4000);
  };

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      fetchUserProfile();
    } else {
      delete axios.defaults.headers.common["Authorization"];
      setUser(null);
    }
  }, [token]);

  useEffect(() => {
    if (!("geolocation" in navigator)) return;

    const handleSuccess = (pos) => {
      setUserLocation({
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      });
      if (pos.coords.heading !== null && !isNaN(pos.coords.heading)) {
        setUserHeading(pos.coords.heading);
      }
    };

    navigator.geolocation.getCurrentPosition(
      handleSuccess,
      () => {
        navigator.geolocation.getCurrentPosition(
          handleSuccess,
          (err) => console.warn("Lokalizacja poczatkowa:", err.message),
          { enableHighAccuracy: false, timeout: 15000, maximumAge: 60000 }
        );
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 }
    );

    const watchId = navigator.geolocation.watchPosition(
      handleSuccess,
      () => {},
      { enableHighAccuracy: false, timeout: 20000, maximumAge: 30000 }
    );

    const handleOrientation = (event) => {
      if (event.webkitCompassHeading) {
        setUserHeading(event.webkitCompassHeading);
      } else if (event.alpha !== null) {
        setUserHeading(360 - event.alpha);
      }
    };

    if (window.DeviceOrientationEvent) {
      window.addEventListener("deviceorientation", handleOrientation, true);
    }
    return () => {
      navigator.geolocation.clearWatch(watchId);
      if (window.DeviceOrientationEvent) {
        window.removeEventListener("deviceorientation", handleOrientation, true);
      }
    };
  }, []);

  const handleLocateMe = () => {
    if (!("geolocation" in navigator)) {
      alert("Twoja przegladarka nie obsluguje geolokalizacji.");
      return;
    }

    const applyPosition = (pos) => {
      setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      if (pos.coords.heading !== null && !isNaN(pos.coords.heading)) {
        setUserHeading(pos.coords.heading);
      }
      showNotify("Zaktualizowano pozycje.");
    };

    navigator.geolocation.getCurrentPosition(
      applyPosition,
      (err) => {
        if (err.code === 3) {
          navigator.geolocation.getCurrentPosition(
            applyPosition,
            (err2) => {
              if (err2.code === 3) {
                alert("Przekroczono limit czasu lokalizacji. Upewnij sie, ze usluga lokalizacji w Windows jest wlaczona.");
              } else if (err2.code === 1) {
                alert("Dostep do lokalizacji zostal zablokowany w przegladarce.");
              } else {
                alert("Nie udalo sie pobrac pozycji: " + err2.message);
              }
            },
            { enableHighAccuracy: false, timeout: 20000, maximumAge: 60000 }
          );
        } else if (err.code === 1) {
          alert("Dostep do lokalizacji zostal zablokowany w przegladarce.");
        } else {
          alert("Blad lokalizacji: " + err.message);
        }
      },
      { enableHighAccuracy: true, timeout: 6000, maximumAge: 30000 }
    );
  };

  const fetchCourts = async () => {
    try {
      let url = `http://localhost:8000/api/courts/nearby?lat=${userLocation.lat}&lng=${userLocation.lng}&radius_meters=15000`;
      if (filterLighting) url += `&has_lighting=true`;
      if (filterRim) url += `&rim_type=${filterRim}`;
      const res = await axios.get(url);
      setCourts(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchCourts();
  }, [userLocation, filterLighting, filterRim]);

  const fetchUserProfile = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/auth/me");
      setUser(res.data);
    } catch {
      localStorage.removeItem("token");
      setToken("");
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    try {
      if (isRegisterMode) {
        const res = await axios.post("http://localhost:8000/api/auth/register", authForm);
        setToken(res.data.access_token);
        localStorage.setItem("token", res.data.access_token);
        setUser(res.data.user);
        showNotify("Rejestracja przebiegla pomyslnie.");
      } else {
        const res = await axios.post("http://localhost:8000/api/auth/login", {
          username_or_email: authForm.username,
          password: authForm.password,
        });
        setToken(res.data.access_token);
        localStorage.setItem("token", res.data.access_token);
        setUser(res.data.user);
        showNotify("Zalogowano pomyslnie.");
      }
      setIsAuthOpen(false);
      setAuthForm({ username: "", email: "", password: "" });
    } catch (err) {
      alert(err.response?.data?.detail || "Blad autoryzacji.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken("");
    setUser(null);
    showNotify("Wylogowano z systemu.");
  };

  const fetchLeaderboard = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/leaderboard");
      setLeaderboardData(res.data);
      setIsLeaderboardOpen(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleMapClick = (latlng) => {
    if (!token) {
      setIsAuthOpen(true);
      return;
    }
    setNewCourtPos(latlng);
    setIsAddCourtOpen(true);
  };

  const handleCreateCourt = async (e) => {
    e.preventDefault();
    if (courtImages.length === 0) {
      alert("Dolacz co najmniej jedno zdjecie obiektu.");
      return;
    }
    const formData = new FormData();
    formData.append("name", courtForm.name);
    formData.append("surface", courtForm.surface);
    formData.append("hoops_count", courtForm.hoops_count);
    formData.append("has_lighting", courtForm.has_lighting);
    formData.append("backboard_type", courtForm.backboard_type);
    formData.append("rim_type", courtForm.rim_type);
    formData.append("net_type", courtForm.net_type);
    formData.append("latitude", newCourtPos.lat);
    formData.append("longitude", newCourtPos.lng);

    for (let i = 0; i < courtImages.length; i++) {
      formData.append("images", courtImages[i]);
    }

    try {
      await axios.post("http://localhost:8000/api/courts", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      showNotify("Obiekt przeslany do weryfikacji.");
      setIsAddCourtOpen(false);
      setCourtImages([]);
      fetchCourts();
    } catch (err) {
      alert(err.response?.data?.detail || "Blad przesylania obiektu.");
    }
  };

  const handleModerateCourt = async (courtId, status) => {
    try {
      await axios.patch(`http://localhost:8000/api/admin/courts/${courtId}/status`, { status });
      showNotify(status === "verified" ? "Obiekt zatwierdzony." : "Zgloszenie odrzucone.");
      fetchCourts();
    } catch (err) {
      alert(err.response?.data?.detail || "Blad moderacji.");
    }
  };

  const handleCheckIn = async (courtId) => {
    if (!token) {
      setIsAuthOpen(true);
      return;
    }
    try {
      const res = await axios.post("http://localhost:8000/api/check-in", {
        court_id: courtId,
        user_lat: userLocation.lat,
        user_lng: userLocation.lng,
      });
      showNotify(res.data.message);
      fetchUserProfile();
      fetchCourts();
    } catch (err) {
      alert(err.response?.data?.detail || "Blad zameldowania.");
    }
  };

  const handleOpenMatches = async (court) => {
    setActiveCourtForMatches(court);
    try {
      const res = await axios.get(`http://localhost:8000/api/courts/${court.id}/matches`);
      setCourtMatches(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateMatch = async (e) => {
    e.preventDefault();
    if (!token) {
      setIsAuthOpen(true);
      return;
    }
    try {
      await axios.post("http://localhost:8000/api/matches", {
        court_id: activeCourtForMatches.id,
        scheduled_time: newMatchForm.scheduled_time,
        max_players: parseInt(newMatchForm.max_players),
      });
      showNotify("Wydarzenie zostalo utworzone.");
      setNewMatchForm({ scheduled_time: "", max_players: 6 });
      const res = await axios.get(`http://localhost:8000/api/courts/${activeCourtForMatches.id}/matches`);
      setCourtMatches(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Blad publikacji meczu.");
    }
  };

  const handleToggleJoinMatch = async (match) => {
    if (!token) {
      setIsAuthOpen(true);
      return;
    }
    try {
      if (match.is_joined) {
        const res = await axios.delete(`http://localhost:8000/api/matches/${match.id}/leave`);
        showNotify(res.data.message);
      } else {
        const res = await axios.post(`http://localhost:8000/api/matches/${match.id}/join`);
        showNotify(res.data.message);
      }
      const updated = await axios.get(`http://localhost:8000/api/courts/${activeCourtForMatches.id}/matches`);
      setCourtMatches(updated.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Blad aktualizacji skladu.");
    }
  };

  return (
    <div className="app-container">
      {}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none">
              <circle cx="12" cy="12" r="10" />
              <path d="M4.93 4.93l4.24 4.24M14.83 14.83l4.24 4.24M14.83 9.17l4.24-4.24M4.93 19.07l4.24-4.24" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Basketball Court Finder</h1>
            <span className="brand-subtitle">System Informacji Geograficznej</span>
          </div>
        </div>

        {}
        <div className="filters-bar">
          <label className={`filter-chip ${filterLighting ? "active" : ""}`}>
            <input
              type="checkbox"
              checked={filterLighting}
              onChange={(e) => setFilterLighting(e.target.checked)}
              style={{ display: "none" }}
            />
            Oswietlenie
          </label>

          <select
            value={filterRim}
            onChange={(e) => setFilterRim(e.target.value)}
            className="filter-select"
          >
            <option value="">Wszystkie obrecze</option>
            <option value="standard_rigid">Sztywne</option>
            <option value="flex_spring">Uchylne (Flex)</option>
            <option value="double_rim">Podwojne</option>
          </select>
        </div>

        {}
        <div className="user-panel">
          <button onClick={fetchLeaderboard} className="btn-leaderboard">
            Ranking graczy
          </button>

          {user ? (
            <div className="user-badge-container">
              <div style={{ textAlign: "right" }}>
                <div className="user-name">{user.username}</div>
                {user.is_admin ? (
                  <span className="user-admin-tag">Administrator</span>
                ) : (
                  <div className="user-stats">
                    {user.rank_title} • <span className="user-xp">{user.xp_points} XP</span>
                  </div>
                )}
              </div>
              <button onClick={handleLogout} className="btn-logout">
                Wyloguj
              </button>
            </div>
          ) : (
            <button onClick={() => setIsAuthOpen(true)} className="btn-login">
              Logowanie / Rejestracja
            </button>
          )}
        </div>
      </header>

      {}
      {notification && (
        <div className="notification-toast">
          <span>•</span> {notification}
        </div>
      )}

      {}
      <div className="map-wrapper">
        <MapContainer
          center={[userLocation.lat, userLocation.lng]}
          zoom={13}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            className="dark-tiles"
          />
          <RecenterMap lat={userLocation.lat} lng={userLocation.lng} />
          <MapClickHandler onMapClick={handleMapClick} />

          {}
          {userLocation && (
            <Marker
              position={[userLocation.lat, userLocation.lng]}
              icon={createRotatedUserIcon(userHeading)}
            >
              <Popup>
                <div style={{ textAlign: "center", padding: "4px" }}>
                  <div style={{ fontWeight: "700", fontSize: "13px" }}>Twoja lokalizacja</div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>
                    {user ? user.username : "Niezalogowany"}
                  </div>
                  <div style={{ fontSize: "11px", color: "#2563eb", marginTop: "2px" }}>
                    Azymut: {Math.round(userHeading)}°
                  </div>
                </div>
              </Popup>
            </Marker>
          )}

          {}
          {courts.map((court) => {
            const isPending = court.status === "pending";
            return (
              <Marker
                key={court.id}
                position={[court.latitude, court.longitude]}
                icon={createCourtMarkerIcon(court)}
              >
                <Popup>
                  <div className="court-popup-card">
                    {court.images && court.images.length > 0 && (
                      <div className="court-popup-image-container">
                        <img
                          src={`http://localhost:8000${court.images[0]}`}
                          alt="Obiekt"
                          className="court-popup-img"
                        />
                        <span className="court-distance-badge">{court.distance_meters} m</span>
                      </div>
                    )}

                    <h3 className="court-popup-title">{court.name}</h3>

                    {isPending && (
                      <div className="status-pending-tag">Oczekuje na weryfikacje</div>
                    )}

                    <div className="tags-row">
                      <span className="court-tag">{court.hoops_count} {court.hoops_count === 1 ? "kosz" : "kosze"}</span>
                      <span className="court-tag">{court.surface}</span>
                      <span className="court-tag">{court.has_lighting ? "Oswietlenie: Tak" : "Oswietlenie: Brak"}</span>
                      <span className="court-tag court-tag-active">Na boisku: {court.active_players_count}</span>
                    </div>

                    <button onClick={() => handleCheckIn(court.id)} className="btn-checkin">
                      Zamelduj sie (+25 XP)
                    </button>

                    <button onClick={() => handleOpenMatches(court)} className="btn-matches-open">
                      Mecze i spotkania 3x3
                    </button>

                    {user?.is_admin && isPending && (
                      <div style={{ marginTop: "10px", padding: "8px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
                        <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", marginBottom: "6px" }}>
                          Moderacja:
                        </div>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            onClick={() => handleModerateCourt(court.id, "verified")}
                            style={{ flex: 1, background: "#16a34a", color: "#fff", border: "none", padding: "6px", borderRadius: "4px", fontSize: "11px", fontWeight: "700", cursor: "pointer" }}
                          >
                            Zatwierdz
                          </button>
                          <button
                            onClick={() => handleModerateCourt(court.id, "rejected")}
                            style={{ flex: 1, background: "#dc2626", color: "#fff", border: "none", padding: "6px", borderRadius: "4px", fontSize: "11px", fontWeight: "700", cursor: "pointer" }}
                          >
                            Odrzuc
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        <button onClick={handleLocateMe} className="btn-locate">
          Moja pozycja
        </button>
      </div>

      {}
      {activeCourtForMatches && (
        <div className="modal-overlay">
          <div className="modal-content wide">
            <div className="modal-header">
              <div>
                <h2 className="modal-title">Spotkania 3x3</h2>
                <div className="modal-subtitle">{activeCourtForMatches.name}</div>
              </div>
              <button onClick={() => setActiveCourtForMatches(null)} className="btn-close">✕</button>
            </div>

            <div className="matches-list">
              {courtMatches.length === 0 ? (
                <div style={{ padding: "16px", textAlign: "center", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1", color: "#64748b", fontSize: "13px" }}>
                  Brak zaplanowanych spotkan. Badz pierwszym organizatorem!
                </div>
              ) : (
                courtMatches.map((m) => (
                  <div key={m.id} className="match-card">
                    <div>
                      <div className="match-time">Termin: {m.scheduled_time}</div>
                      <div className="match-details">
                        Organizator: <b>{m.creator_username}</b> • Sklad: <b>{m.joined_count}/{m.max_players}</b>
                      </div>
                    </div>
                    <button
                      onClick={() => handleToggleJoinMatch(m)}
                      disabled={!m.is_joined && m.joined_count >= m.max_players}
                      className={`btn-join ${m.is_joined ? "joined" : ""} ${!m.is_joined && m.joined_count >= m.max_players ? "disabled" : ""}`}
                    >
                      {m.is_joined ? "Zapisany (Opusc)" : m.joined_count >= m.max_players ? "Komplet" : "Dolacz do skladu"}
                    </button>
                  </div>
                ))
              )}
            </div>

            <form onSubmit={handleCreateMatch} className="form-group" style={{ borderTop: "1px solid #f1f5f9", paddingTop: "14px" }}>
              <div style={{ fontSize: "12px", fontWeight: "700", color: "#475569" }}>Utworz nowe spotkanie</div>
              <label className="input-label">
                Termin rozpoczecia:
                <input
                  type="datetime-local"
                  value={newMatchForm.scheduled_time}
                  onChange={(e) => setNewMatchForm({ ...newMatchForm, scheduled_time: e.target.value })}
                  required
                  className="form-input"
                />
              </label>

              <label className="input-label">
                Limit graczy w meczu:
                <input
                  type="number"
                  min="2"
                  max="12"
                  value={newMatchForm.max_players}
                  onChange={(e) => setNewMatchForm({ ...newMatchForm, max_players: e.target.value })}
                  className="form-input"
                />
              </label>

              <button type="submit" className="btn-submit">
                Opublikuj w harmonogramie
              </button>
            </form>
          </div>
        </div>
      )}

      {}
      {isAuthOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">{isRegisterMode ? "Rejestracja konta" : "Logowanie"}</h2>
              <button onClick={() => setIsAuthOpen(false)} className="btn-close">✕</button>
            </div>
            <form onSubmit={handleAuth} className="form-group">
              <input
                type="text"
                placeholder={isRegisterMode ? "Nazwa uzytkownika" : "Login lub e-mail"}
                value={authForm.username}
                onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                required
                className="form-input"
              />
              {isRegisterMode && (
                <input
                  type="email"
                  placeholder="Adres e-mail"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                  required
                  className="form-input"
                />
              )}
              <input
                type="password"
                placeholder="Haslo"
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                required
                className="form-input"
              />
              <button type="submit" className="btn-submit">
                {isRegisterMode ? "Zaloz konto" : "Zaloguj sie"}
              </button>
            </form>
            <div style={{ textAlign: "center", marginTop: "14px", fontSize: "13px" }}>
              <span
                onClick={() => setIsRegisterMode(!isRegisterMode)}
                style={{ color: "#2563eb", cursor: "pointer", fontWeight: "600" }}
              >
                {isRegisterMode ? "Masz juz konto? Zaloguj sie" : "Nie masz konta? Zarejestruj sie"}
              </span>
            </div>
          </div>
        </div>
      )}

      {}
      {isAddCourtOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Zgloszenie obiektu</h2>
              <button onClick={() => setIsAddCourtOpen(false)} className="btn-close">✕</button>
            </div>
            <form onSubmit={handleCreateCourt} className="form-group">
              <input
                type="text"
                placeholder="Nazwa boiska (np. Orlik Miejski)"
                value={courtForm.name}
                onChange={(e) => setCourtForm({ ...courtForm, name: e.target.value })}
                required
                className="form-input"
              />

              <label className="input-label">
                Nawierzchnia:
                <select
                  value={courtForm.surface}
                  onChange={(e) => setCourtForm({ ...courtForm, surface: e.target.value })}
                  className="form-input"
                >
                  <option value="asfalt">Asfalt</option>
                  <option value="tartan">Tartan (Poliuretan)</option>
                  <option value="beton">Beton</option>
                  <option value="parkiet">Hala / Parkiet</option>
                </select>
              </label>

              <div style={{ display: "flex", gap: "10px" }}>
                <label className="input-label" style={{ flex: 1 }}>
                  Liczba koszy:
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={courtForm.hoops_count}
                    onChange={(e) => setCourtForm({ ...courtForm, hoops_count: parseInt(e.target.value) })}
                    className="form-input"
                  />
                </label>
                <label className="input-label" style={{ flex: 1 }}>
                  Obrecz:
                  <select
                    value={courtForm.rim_type}
                    onChange={(e) => setCourtForm({ ...courtForm, rim_type: e.target.value })}
                    className="form-input"
                  >
                    <option value="standard_rigid">Sztywna</option>
                    <option value="flex_spring">Uchylna</option>
                    <option value="double_rim">Podwojna</option>
                  </select>
                </label>
              </div>

              <label className="input-label">
                Siatka:
                <select
                  value={courtForm.net_type}
                  onChange={(e) => setCourtForm({ ...courtForm, net_type: e.target.value })}
                  className="form-input"
                >
                  <option value="lancuchowa">Lancuchowa stalowa</option>
                  <option value="sznurkowa">Sznurkowa nylonowa</option>
                  <option value="brak">Brak siatki</option>
                </select>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: "600", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={courtForm.has_lighting}
                  onChange={(e) => setCourtForm({ ...courtForm, has_lighting: e.target.checked })}
                />
                Obiekt posiada oswietlenie nocne
              </label>

              <label className="input-label">
                Zdjecie dowodowe do moderacji:
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setCourtImages(e.target.files)}
                  required
                  style={{ marginTop: "4px", fontSize: "12px" }}
                />
              </label>

              <button type="submit" className="btn-submit">
                Przeslij do weryfikacji
              </button>
            </form>
          </div>
        </div>
      )}

      {}
      {isLeaderboardOpen && (
        <div className="modal-overlay">
          <div className="modal-content wide">
            <div className="modal-header">
              <div>
                <h2 className="modal-title">Tabela liderow</h2>
                <div className="modal-subtitle">Najbardziej aktywni gracze</div>
              </div>
              <button onClick={() => setIsLeaderboardOpen(false)} className="btn-close">✕</button>
            </div>

            <div className="leaderboard-list">
              {leaderboardData.map((player, index) => {
                const rankClass = index === 0 ? "top1" : index === 1 ? "top2" : index === 2 ? "top3" : "";
                return (
                  <div key={player.username} className="leaderboard-row">
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span className={`leaderboard-rank ${rankClass}`}>
                        {index + 1}
                      </span>
                      <div>
                        <div style={{ fontWeight: "700", fontSize: "14px" }}>{player.username}</div>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>{player.rank_title} (Poz. {player.level})</div>
                      </div>
                    </div>
                    <div className="leaderboard-xp">
                      {player.xp_points} XP
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
