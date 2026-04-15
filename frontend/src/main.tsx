import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Signals } from "./pages/Signals";
import { Scanner } from "./pages/Scanner";
import { HedgeFunds } from "./pages/HedgeFunds";
import { Papers } from "./pages/Papers";
import { Macro } from "./pages/Macro";
import { WatchlistPage } from "./pages/Watchlist";
import { Journal } from "./pages/Journal";
import { Risk } from "./pages/Risk";
import { AIAnalysis } from "./pages/AIAnalysis";
import { Discovery } from "./pages/Discovery";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discovery" element={<Discovery />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/hedgefunds" element={<HedgeFunds />} />
          <Route path="/papers" element={<Papers />} />
          <Route path="/macro" element={<Macro />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/ai" element={<AIAnalysis />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
