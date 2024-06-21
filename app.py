import os
from flask import Flask, render_template, jsonify
from supabase_client import supabase
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import json
from collections import defaultdict
from datetime import datetime, timedelta
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')
    
def get_week_range(date):
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end

@app.route('/api/trades')
def get_trades():
    try:
        response = supabase.table('trade_history').select('*').execute()
        trades = response.data

        trade_summary = defaultdict(lambda: {
            'count': 0,
            'total_profit_loss': 0,
            'total_volume': 0,
            'trade_durations': [],
            'trades': [],
            'win_count': 0,
            'loss_count': 0,
            'win_loss_status': 'win'
        })

        for trade in trades:
            date = trade['time'].split('T')[0]
            trade_summary[date]['count'] += 1
            trade_summary[date]['total_profit_loss'] += trade['profit']
            trade_summary[date]['total_volume'] += trade['volume']
            trade_summary[date]['trades'].append(trade)
            if trade['profit'] > 0:
                trade_summary[date]['win_count'] += 1
            else:
                trade_summary[date]['loss_count'] += 1
            start_time = datetime.fromisoformat(trade['time'])
            end_time = datetime.fromisoformat(trade['close_time']) if trade['close_time'] else start_time
            duration = (end_time - start_time).total_seconds() / 60  # Convert duration to minutes
            trade_summary[date]['trade_durations'].append(duration)

        events = []
        for date, summary in trade_summary.items():
            avg_duration = sum(summary['trade_durations']) / len(summary['trade_durations']) if summary['trade_durations'] else 0
            summary['win_loss_status'] = 'win' if summary['total_profit_loss'] >= 0 else 'loss'
            events.append({
                'title': f"Trades: {summary['count']}, P/L: {summary['total_profit_loss']}, Vol: {summary['total_volume']}, Avg Dur: {avg_duration:.2f} min",
                'start': date,
                'backgroundColor': 'green' if summary['win_loss_status'] == 'win' else 'red',
                'extendedProps': summary
            })

        # Weekly summary
        weekly_summary = defaultdict(lambda: {
            'count': 0,
            'total_profit_loss': 0,
            'total_volume': 0,
            'win_count': 0,
            'loss_count': 0,
        })

        for date, summary in trade_summary.items():
            date_obj = datetime.fromisoformat(date)
            week_start, week_end = get_week_range(date_obj)
            week_key = f"{week_start.date()} - {week_end.date()}"
            weekly_summary[week_key]['count'] += summary['count']
            weekly_summary[week_key]['total_profit_loss'] += summary['total_profit_loss']
            weekly_summary[week_key]['total_volume'] += summary['total_volume']
            weekly_summary[week_key]['win_count'] += summary['win_count']
            weekly_summary[week_key]['loss_count'] += summary['loss_count']

        for week, summary in weekly_summary.items():
            events.append({
                'title': f"Week Summary: Trades: {summary['count']}, P/L: {summary['total_profit_loss']}, Vol: {summary['total_volume']}, Wins: {summary['win_count']}, Losses: {summary['loss_count']}",
                'start': week.split(' - ')[0],
                'end': (datetime.fromisoformat(week.split(' - ')[1]) + timedelta(days=1)).date().isoformat(),
                'backgroundColor': 'blue',
                'extendedProps': summary
            })

        # Monthly summary
        monthly_summary = defaultdict(lambda: {
            'count': 0,
            'total_profit_loss': 0,
            'total_volume': 0,
            'win_count': 0,
            'loss_count': 0,
        })

        for date, summary in trade_summary.items():
            date_obj = datetime.fromisoformat(date)
            month_key = date_obj.strftime("%Y-%m")
            monthly_summary[month_key]['count'] += summary['count']
            monthly_summary[month_key]['total_profit_loss'] += summary['total_profit_loss']
            monthly_summary[month_key]['total_volume'] += summary['total_volume']
            monthly_summary[month_key]['win_count'] += summary['win_count']
            monthly_summary[month_key]['loss_count'] += summary['loss_count']

        for month, summary in monthly_summary.items():
            month_start = datetime.strptime(month, "%Y-%m").date()
            month_end = (month_start.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            events.append({
                'title': f"Month Summary: Trades: {summary['count']}, P/L: {summary['total_profit_loss']}, Vol: {summary['total_volume']}, Wins: {summary['win_count']}, Losses: {summary['loss_count']}",

                'start': month_start.isoformat(),

                'end': month_end.isoformat(),

                'backgroundColor': 'purple',

                'extendedProps': summary

            })

        return jsonify(events)

    except Exception as e:

        logging.error(f"Error fetching trades: {e}")

        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
