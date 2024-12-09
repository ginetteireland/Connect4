const EventEmitter = require('events')

class Game extends EventEmitter {
  static dimensionX = 7
  static dimensionY = 6
  static maxMoves = this.dimensionX * this.dimensionY
  static combo = 4

  players = 1
  lastPlayed = 2
  moves = 0

  constructor (id) {
    super()

    this.id = id

    this.board = []
    for (let x = 0; x < Game.dimensionX; ++x) this.board.push([])
  }

  async dropPiece (player, col) {
    if (player < 1 || player > 2) throw Error('invalid player')
    if (this.players < 2) throw Error('not enough players')
    if (player === this.lastPlayed) throw Error('not current turn')

    if (col in this.board) {
      if (this.board[col].length >= Game.dimensionY) throw Error('column full')

      this.board[col].push(player)
      ++this.moves
      this.lastPlayed = player

      this.emit('move', player, col)
    } else throw Error('invalid column')
  }

  assessWinner (player, lastMove) {
    const row = this.board[lastMove].length - 1

    const won = (
      (this.countChain(player, lastMove, row, -1, 0) + this.countChain(player, lastMove, row, 1, 0)) - 1 >= Game.combo || // Vertical
      (this.countChain(player, lastMove, row, 0, -1) + this.countChain(player, lastMove, row, 0, 1)) - 1 >= Game.combo || // Horizontal
      (this.countChain(player, lastMove, row, -1, -1) + this.countChain(player, lastMove, row, 1, 1)) - 1 >= Game.combo || // Positive slope diagonal
      (this.countChain(player, lastMove, row, 1, -1) + this.countChain(player, lastMove, row, -1, 1)) - 1 >= Game.combo // Negative slope diagonal
    )

    if (won) {
      this.emit('win', player)

      console.log('player', player, 'won game', this.id)
    } else if (this.moves >= Game.maxMoves) {
      this.emit('draw')

      console.log(this.id, 'resulted in a draw')
    }
  }

  countChain (player, col, row, colIncrement, rowIncrement) {
    let count = 0

    while (col > -1 && col < this.board.length && row > -1 && row < this.board[col].length) {
      if (this.board[col][row] !== player) return count
      else ++count

      col += colIncrement
      row += rowIncrement
    }

    return count
  }
}

class Manager {
  games = new Map()

  createGame () {
    let id
    do {
      const base = Math.round((process.uptime() * 1000) % 0xFFFF).toString(16).toUpperCase()
      const pad = '0'.repeat(4 - base.length)

      id = pad + base
    } while (this.games.has(id))

    const game = new Game(id)
    this.games.set(game.id, game)

    return game
  }

  getGame (id) {
    return this.games.get(id.toUpperCase())
  }

  destroyGame (id) {
    this.games.delete(id)
  }
}

const manager = new Manager()

function handleGame (ws, req, game, player) {
  ws.on('message', req.formatWSMsg(({ command, data }) => {
    switch (command.toUpperCase()) {
      case 'PLAY': {
        const position = parseInt(data)
        if (isNaN(position)) ws.send('ERROR:invalid position')

        game.dropPiece(player, position)
          .then(() => {
            console.table({
              game: game.id,
              player,
              position
            })

            ws.send('ACK')

            game.assessWinner(player, position)
          })
          .catch((err) => ws.send(`ERROR:${err.message}`))

        break
      }
      default: ws.send('ERROR:unknown command')
    }
  }))

  ws.on('close', (code) => {
    if (code !== 1000) console.warn(req.connection.remoteAddress, 'disconnected from game', game.id)

    game.emit('terminate')
  })
  game.on('terminate', () => {
    ws.send('TERMINATED')

    ws.close(1000)

    req.manager.destroyGame(game.id)
  })

  game.on('start', () => ws.send('GAMESTART'))

  game.on('move', (mover, col) => {
    if (mover !== player) ws.send(`OPPONENT:${col}`)
  })

  game.on('win', (winner) => {
    ws.send(winner === player ? 'WIN' : 'LOSS')

    ws.close(1000)

    req.manager.destroyGame(game.id)
  })

  game.on('draw', (winner) => {
    ws.send('DRAW')

    ws.close(1000)

    req.manager.destroyGame(game.id)
  })
}

module.exports = function (req, res, next) {
  req.manager = manager
  req.handleGame = handleGame

  next()
}
