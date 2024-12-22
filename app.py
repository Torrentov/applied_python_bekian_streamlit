import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import datetime
import matplotlib.dates as mdates



MONTH_TO_SEASON = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter"
}


def process_main_page():
    show_main_page()
    process_side_bar_inputs()


def show_main_page():
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="auto",
        page_title="Temperature analysis"
    )


def get_city_stats(data):
    data['moving_avg'] = data['temperature'].rolling(window=30).mean()
    data['moving_std'] = data['temperature'].rolling(window=30).std()
    data['is_anomaly'] = (data['temperature'] > data['moving_avg'] + 2 * data['moving_std']) | \
                         (data['temperature'] < data['moving_avg'] - 2 * data['moving_std'])
    
    seasonal_stats = data.groupby(['season'])['temperature'].agg(['mean', 'std']).reset_index()

    temp_stats = {
        "mean": int(round(data['temperature'].mean(), 0)),
        "min": int(round(data['temperature'].min(), 0)),
        "max": int(round(data['temperature'].max(), 0))
    }

    data['trend'] = np.poly1d(np.polyfit(data.index.to_numpy(), data['temperature'].to_numpy(), 1))(data.index.to_numpy())

    data.index = data["timestamp"]

    return data, seasonal_stats, temp_stats


def process_side_bar_inputs():
    historical_file, city, api_key = sidebar_input_features()

    if historical_file:
        historical_data = pd.read_csv(historical_file)

        historical_data = historical_data.loc[historical_data['city'] == city]

        data, seasonal_stats, temp_stats = get_city_stats(historical_data)

        st.header("Historical stats")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Minimal temperature", temp_stats["min"])
        with col2:
            st.metric("Maximal temperature", temp_stats["max"])
        with col3:
            st.metric("Mean temperature", temp_stats["mean"])

        anomalous_temps = data.loc[data["is_anomaly"] == True]

        fig, ax = plt.subplots()
        fig.set_figheight(3)
        fig.set_figwidth(10)

        ax.plot(data["temperature"], label="Temperature")
        ax.plot(data["moving_avg"], label="Moving average")
        ax.plot(data["trend"], label="Trend")
        ax.scatter(anomalous_temps.index, anomalous_temps["temperature"], label="Anomalies", color="red")

        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=300))
        plt.gcf().autofmt_xdate()   

        plt.legend()
        st.pyplot(fig)

        if api_key:
            response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}")

            if response.status_code == 200:
                response = response.json()[0]
                lat = response['lat']
                lon = response['lon']

                response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}" \
                                        f"&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={api_key}&units=metric")
                
                current_temp = response.json()['main']['temp']

                st.write(f"Current temperature in {city}: {int(round(current_temp, 0))}°C")

                current_season = MONTH_TO_SEASON[datetime.datetime.now().month]

                mean_season_temp = seasonal_stats.loc[seasonal_stats['season'] == current_season, 'mean'].iloc[0]
                std_season_temp = seasonal_stats.loc[seasonal_stats['season'] == current_season, 'std'].iloc[0]

                if (current_temp > mean_season_temp + 2 * std_season_temp) or (current_temp < mean_season_temp - 2 * std_season_temp):
                    st.write(f"Current temperature is anomalous for {current_season} in {city}")
                else:
                    st.write(f"Current temperature is normal for {current_season} in {city}")

            elif response.status_code == 401 and response.json().get("message") == "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.":
                st.error("Incorrent API key")
            else:
                st.error("An error occured while getting current temperature. Please try again later")
        else:
            st.info("Enter API key if you want to see current temperature")

        st.table(data=seasonal_stats)

    
def sidebar_input_features():
    st.sidebar.header("Historical data")
    uploaded_file = st.sidebar.file_uploader("Upload .csv file with historical data", type="csv")

    st.sidebar.header("City selection")
    cities = ['New York', 'London', 'Paris', 'Tokyo', 'Moscow', 'Sydney',
              'Berlin', 'Beijing', 'Rio de Janeiro', 'Dubai', 'Los Angeles',
              'Singapore', 'Mumbai', 'Cairo', 'Mexico City']
    city = st.sidebar.selectbox("Choose the city", cities)

    st.sidebar.header("API key")
    api_key = st.sidebar.text_input("Enter your OpenWeatherMap API key")

    return uploaded_file, city, api_key


if __name__ == "__main__":
    process_main_page()
