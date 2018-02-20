import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';

class App extends Component {
  componentDidMount() {
    const url = 'api/info';

    fetch(url)
      .then(function(response) {
        if (response.status >= 400) {
          return `Invalid request status: ${response.status}`;
        }
        return response.json();
      })
      .then(function(data) {
        this.setState({ appName: data.appName });
      }.bind(this));
  }

  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">{this.state.appName}</h1>
        </header>
        <p className="App-intro">
          Chops example web application.
        </p>
      </div>
    );
  }

  state = {
    appName: 'Awaiting for response...',
  }
}

export default App;
