import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

export function useLiveDashboard(pollInterval = 3000) {
  const [stats, setStats] = useState({
    total_registered: 0,
    target: 500,
    progress_percentage: 0,
    viral_coefficient: 0.0,
    blended_cac_inr: 2000.0,
    seed_count: 0,
    viral_count: 0,
    rewards_unlocked: 0,
    colleges: {}
  });

  const [feed, setFeed] = useState([]);
  const [ambassadors, setAmbassadors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastSync, setLastSync] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchAllData = async () => {
      try {
        const [statsRes, feedRes, ambRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/api/stats`, { signal: controller.signal }),
          axios.get(`${API_BASE_URL}/api/feed`, { signal: controller.signal }),
          axios.get(`${API_BASE_URL}/ambassadors`, { signal: controller.signal })
        ]);

        if (isMounted) {
          setStats(statsRes.data);
          setFeed(feedRes.data.feed || []);
          setAmbassadors(ambRes.data.ambassadors || []);
          setLastSync(new Date());
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (axios.isCancel(err)) return;
        console.error("Dashboard sync error:", err);
        if (isMounted) {
          setError("Reconnecting to backend...");
        }
      }
    };

    fetchAllData();
    const intervalId = setInterval(fetchAllData, pollInterval);

    return () => {
      isMounted = false;
      controller.abort();
      clearInterval(intervalId);
    };
  }, [pollInterval]);

  return { stats, feed, ambassadors, loading, lastSync, error };
}
