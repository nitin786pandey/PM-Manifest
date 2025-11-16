import typing as t

import pandas as pd


def ensure_datetime(df: pd.DataFrame, time_field: str = "createdAt") -> pd.DataFrame:
	if time_field in df.columns and not pd.api.types.is_datetime64_any_dtype(df[time_field]):
		df[time_field] = pd.to_datetime(df[time_field], errors="coerce", utc=True)
	return df


def timeseries_group(df: pd.DataFrame, time_field: str = "createdAt", freq: str = "M") -> pd.DataFrame:
	df = ensure_datetime(df, time_field=time_field)
	if time_field not in df.columns:
		return pd.DataFrame()
	return df.set_index(time_field).sort_index()


def compute_unique_sessions(df: pd.DataFrame, session_field: str) -> int:
	if session_field not in df.columns:
		return 0
	return df[session_field].nunique(dropna=True)


def compute_total_sales(df_checkout: pd.DataFrame, amount_field: str = "eventProperties.totalAmountUSD") -> float:
	if amount_field not in df_checkout.columns:
		return 0.0
	return float(pd.to_numeric(df_checkout[amount_field], errors="coerce").fillna(0).sum())


def compute_aov(df_checkout: pd.DataFrame, session_field: str) -> float:
	orders = df_checkout.shape[0]
	if orders == 0:
		return 0.0
	amount_field = "eventProperties.totalAmountUSD"
	if amount_field not in df_checkout.columns:
		return 0.0
	total = pd.to_numeric(df_checkout[amount_field], errors="coerce").fillna(0).sum()
	return float(total) / float(orders) if orders else 0.0


def compute_conversion_rate(
	sessions_with_orders: int,
	total_sessions: int,
) -> float:
	if total_sessions <= 0:
		return 0.0
	return (sessions_with_orders / total_sessions) * 100.0


def filter_event(df: pd.DataFrame, event_name: str) -> pd.DataFrame:
	if "eventName" not in df.columns:
		return df.iloc[0:0]
	return df[df["eventName"] == event_name]


def compute_interaction_rate(
	df_sessions: pd.DataFrame,
	has_interacted_field: str = "hasInteracted",
	session_field: str = "visitorSessionId",
) -> float:
	"""
	Defaults to sessions with hasInteracted=True divided by all sessions.
	"""
	if session_field not in df_sessions.columns:
		return 0.0
	all_sessions = df_sessions[session_field].nunique(dropna=True)
	if all_sessions == 0:
		return 0.0
	if has_interacted_field not in df_sessions.columns:
		return 0.0
	interacted_sessions = df_sessions[df_sessions[has_interacted_field] == True][session_field].nunique(dropna=True)  # noqa: E712
	return (interacted_sessions / all_sessions) * 100.0


def breakdown_by_field(
	df: pd.DataFrame,
	breakdown_field: str,
	metrics: t.Dict[str, t.Callable[[pd.DataFrame], t.Any]],
) -> pd.DataFrame:
	"""
	Apply a dict of metric functions to grouped data.
	Each metric function receives a sub-DataFrame and returns a scalar.
	"""
	if breakdown_field not in df.columns:
		return pd.DataFrame()
	results = []
	for key, group in df.groupby(breakdown_field, dropna=False):
		row = {"key": key}
		for metric_name, fn in metrics.items():
			try:
				row[metric_name] = fn(group)
			except Exception:
				row[metric_name] = None
		results.append(row)
	return pd.DataFrame(results)


def compute_interaction_rate_from_counts(clicks: float, visits: float) -> float:
	if visits <= 0:
		return 0.0
	return (float(clicks) / float(visits)) * 100.0


def make_two_periods(compare_days: int = 28) -> t.Tuple[str, str, str, str]:
	"""
	Returns (gte_current, lte_current, gte_previous, lte_previous) in ES 'now' syntax.
	- Current: now-<compare_days>d/d .. now
	- Previous: now-<2*compare_days>d/d .. now-<compare_days>d/d
	"""
	cur_gte = f"now-{compare_days}d/d"
	cur_lte = "now"
	prev_gte = f"now-{2*compare_days}d/d"
	prev_lte = f"now-{compare_days}d/d"
	return cur_gte, cur_lte, prev_gte, prev_lte


def compute_shift_share_drivers(
	total_clicks_cur: float,
	total_visits_cur: float,
	total_clicks_prev: float,
	total_visits_prev: float,
	per_key_clicks_cur: t.Dict[str, float],
	per_key_visits_cur: t.Dict[str, float],
	per_key_clicks_prev: t.Dict[str, float],
	per_key_visits_prev: t.Dict[str, float],
) -> t.Dict[str, float]:
	"""
	Decompose overall rate delta into:
	- rate_effect: sum_i w_i_avg * (r_i_cur - r_i_prev)
	- mix_effect: sum_i (w_i_cur - w_i_prev) * r_i_prev
	- volume_effect: 0 for rate metrics (weights normalized)
	Weights w_i are visit shares. Uses simple average weight across periods.
	"""
	def safe_rate(c, v) -> float:
		return (c / v) if v else 0.0
	def safe_share(v, total) -> float:
		return (v / total) if total else 0.0
	r_cur = safe_rate(total_clicks_cur, total_visits_cur)
	r_prev = safe_rate(total_clicks_prev, total_visits_prev)
	keys = set(list(per_key_visits_cur.keys()) + list(per_key_visits_prev.keys()))
	rate_effect = 0.0
	mix_effect = 0.0
	for k in keys:
		v_cur = per_key_visits_cur.get(k, 0.0)
		v_prev = per_key_visits_prev.get(k, 0.0)
		c_cur = per_key_clicks_cur.get(k, 0.0)
		c_prev = per_key_clicks_prev.get(k, 0.0)
		r_i_cur = safe_rate(c_cur, v_cur)
		r_i_prev = safe_rate(c_prev, v_prev)
		w_i_cur = safe_share(v_cur, total_visits_cur)
		w_i_prev = safe_share(v_prev, total_visits_prev)
		w_i_avg = (w_i_cur + w_i_prev) / 2.0
		rate_effect += w_i_avg * (r_i_cur - r_i_prev)
		mix_effect += (w_i_cur - w_i_prev) * r_i_prev
	volume_effect = 0.0
	total_delta = r_cur - r_prev
	# Minor numerical balancing: ensure components sum to delta
	residual = total_delta - (rate_effect + mix_effect + volume_effect)
	rate_effect += residual
	return {
		"rate_effect": float(rate_effect * 100.0),
		"mix_effect": float(mix_effect * 100.0),
		"volume_effect": float(volume_effect),
		"delta_rate": float(total_delta * 100.0),
	}

