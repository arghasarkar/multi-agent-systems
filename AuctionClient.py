import socket
import random
import copy
import math

class AuctionClient(object):
    """A client for bidding with the AucionRoom"""
    def __init__(self, host="localhost", port=8020, mybidderid="1221352", verbose=False):
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host,port))
        forbidden_chars = set(""" '".,;:{}[]()""")
        if mybidderid:
            if len(mybidderid) == 0 or any((c in forbidden_chars) for c in mybidderid):
                print("""mybidderid cannot contain spaces or any of the following: '".,;:{}[]()!""")
                raise ValueError
            self.mybidderid = mybidderid
        else:
            self.mybidderid = raw_input("Input team / player name : ").strip()  # this is the only thing that distinguishes the clients
            while len(self.mybidderid) == 0 or any((c in forbidden_chars) for c in self.mybidderid):
              self.mybidderid = raw_input("""You input an empty string or included a space  or one of these '".,;:{}[]() in your name which is not allowed (_ or / are all allowed)\n for example Emil_And_Nischal is okay\nInput team / player name: """).strip()
        self.sock.send(self.mybidderid.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if self.verbose:
            print("Have received response of %s" % ' '.join(x))
        if(x[0] != "Not" and len(data) != 0):
          self.numberbidders = int(x[0])
          if self.verbose:
              print("Number of bidders: %d" % self.numberbidders)
          self.numtypes = int(x[1])
          if self.verbose:
              print("Number of types: %d" % self.numtypes)
          self.numitems = int(x[2])
          if self.verbose:
              print("Items in auction: %d" % self.numitems)
          self.maxbudget = int(x[3])
          if self.verbose:
              print("Budget: %d" % self.maxbudget)
          self.neededtowin = int(x[4])
          if self.verbose:
              print("Needed to win: %d" % self.neededtowin)
          self.order_known = "True" == x[5]
          if self.verbose:
              print("Order known: %s" % self.order_known)
          self.auctionlist = []
          self.winnerpays = int(x[6])
          if self.verbose:
              print("Winner pays: %d" % self.winnerpays)
          self.values = {}
          self.artists = {}
          order_start = 7
          if self.neededtowin > 0:
              self.values = None
              for i in range(7, 7+(self.numtypes*2), 2):
                  self.artists[x[i]] = int(x[i+1])
                  order_start += 2
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
          else:
              for i in range(7, 7+(self.numtypes*3), 3):
                  self.artists[x[i]] = int(x[i+1])
                  self.values[x[i]] = int(x[i+2])
                  order_start += 3
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
                  print ("Values: %s" % str(self.values))

          if self.order_known:
              for i in range(order_start, order_start+self.numitems):
                  self.auctionlist.append(x[i])
              if self.verbose:
                  print("Auction order: %s" % str(self.auctionlist))

        self.sock.send('connected '.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if x[0] != 'players':
            print("Did not receive list of players!")
            raise IOError
        if len(x) != self.numberbidders + 2:
            print("Length of list of players received does not match numberbidders!")
            raise IOError
        if self.verbose:
         print("List of players: %s" % str(' '.join(x[1:])))

        self.players = []

        for player in range(1, self.numberbidders + 1):
          self.players.append(x[player])

        self.sock.send('ready '.encode("utf-8"))

        self.standings = {name: {artist : 0 for artist in self.artists} for name in self.players}
        for name in self.players:
          self.standings[name]["money"] = self.maxbudget

        # My variables

        # Game 1
        self.game_num = 0
        self.game_1_first_artist = None
        self.paintings_won = 0
        self.block_first_count = 0

        # Game 2
        self.first_painting = ""
        self.acquired_first_painting = False
        self.second_painting = ""

        # Game 3
        self.total_value_of_paintings = 0
        self.total_value_left = 0

    def play_auction(self):
        winnerarray = []
        winneramount = []
        done = False
        while not done:
            data = self.sock.recv(5024).decode('utf_8')
            x = data.split(" ")
            if x[0] != "done":
                if x[0] == "selling":
                    currentitem = x[1]
                    if not self.order_known:
                        self.auctionlist.append(currentitem)
                    if self.verbose:
                        print("Item on sale is %s" % currentitem)
                    bid = self.determinebid(self.numberbidders, self.neededtowin, self.artists, self.values, len(winnerarray), self.auctionlist, winnerarray, winneramount, self.mybidderid, self.players, self.standings, self.winnerpays)
                    if self.verbose:
                        print("Bidding: %d" % bid)
                    self.sock.send(str(bid).encode("utf-8"))
                    data = self.sock.recv(5024).decode('utf_8')
                    x = data.split(" ")
                    if x[0] == "draw":
                        winnerarray.append(None)
                        winneramount.append(0)
                    if x[0] == "winner":
                        winnerarray.append(x[1])
                        winneramount.append(int(x[3]))
                        self.standings[x[1]][currentitem] += 1
                        self.standings[x[1]]["money"] -= int(x[3])
            else:
                done = True
                if self.verbose:
                    if self.mybidderid in x[1:-1]:
                        print("I won! Hooray!")
                    else:
                        print("Well, better luck next time...")
        self.sock.close()

    def determinebid(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        '''You have all the variables and lists you could need in the arguments of the function,
        these will always be updated and relevant, so all you have to do is use them.
        Write code to make your bot do a lot of smart stuff to beat all the other bots. Good luck,
        and may the games begin!'''

        '''
        numberbidders is an integer displaying the amount of people playing the auction game.

        wincondition is an integer. A postiive integer means that whoever gets that amount of a single type\part{}
        of item wins, whilst 0 means each itemtype will have a value and the winner will be whoever accumulates the
        highest total value before all items are auctioned or everyone runs out of funds.

        artists will be a dict of the different item types as keys with the total number of that type on auction as elements.

        values will be a dict of the item types as keys and the type value if wincondition == 0. Else value == None.

        rd is the current round in 0 based indexing.

        itemsinauction is a list where at index "rd" the item in that round is being sold is displayed. Note that it will either be as long as the sum of all the number of the items (as in "artists") in which case the full auction order is pre-announced and known, or len(itemsinauction) == rd+1, in which case it only holds the past and current items, the next item to be auctioned is unknown.

        winnerarray is a list where at index "rd" the winner of the item sold in that round is displayed.

        winneramount is a list where at index "rd" the amount of money paid for the item sold in that round is displayed.

        example: I will now construct a sentence that would be correct if you substituted the outputs of the lists:
        In round 5 winnerarray[4] bought itemsinauction[4] for winneramount[4] pounds/dollars/money unit.

        mybidderid is your name: if you want to reference yourself use that.

        players is a list containing all the names of the current players.

        standings is a set of nested dictionaries (standings is a dictionary that for each person has another dictionary
        associated with them). standings[name][artist] will return how many paintings "artist" the player "name" currently has.
        standings[name]['money'] (remember quotes for string, important!) returns how much money the player "name" has left.

            standings[mybidderid] is the information about you.
            I.e., standings[mybidderid]['money'] is the budget you have left.

        winnerpays is an integer representing which bid the highest bidder pays. If 0, the highest bidder pays their own bid,
        but if 1, the highest bidder instead pays the second highest bid (and if 2 the third highest, ect....). Note though that if you win, you always pay at least 1 (even if the second-highest was 0).

        Don't change any of these values, or you might confuse your bot! Just use them to determine your bid.
        You can also access any of the object variables defined in the constructor (though again don't change these!), or declare your own to save state between determinebid calls if you so wish.

        determinebid should return your bid as an integer. Note that if it exceeds your current budget (standings[mybidderid]['money']), the auction server will simply set it to your current budget.

        Good luck!
        '''

        # Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known.
        if (wincondition > 0) and (winnerpays == 0) and self.order_known:
            self.game_num = 1

            return self.first_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known.
        if (wincondition > 0) and (winnerpays == 0) and not self.order_known:
            self.game_num = 2

            return self.second_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 3: Highest total value wins, highest bidder pays own bid, auction order known.
        if (wincondition == 0) and (winnerpays == 0) and self.order_known:
            self.game_num = 3

            return self.third_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known.
        if (wincondition == 0) and (winnerpays == 1) and self.order_known:
            self.game_num = 4

            return self.fourth_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Though you will only be assessed on these four cases, feel free to try your hand at others!
        # Otherwise, this just returns a random bid.
        return self.random_bid(standings[mybidderid]['money'])


    def random_bid(self, budget):
        """Returns a random bid between 1 and left over budget."""
        return int(budget*random.random()+1)


    def first_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known."""

        # My budget left
        assets = standings[mybidderid]
        budget = assets['money']

        first_artist = self.first_n_artists(artists, itemsinauction, wincondition, 1)
        second_artist = self.first_n_artists(artists, itemsinauction, wincondition, 2)

        current_artist = itemsinauction[rd]
        # Bid highly to prevent anyone from getting the first artist
        if current_artist == first_artist and self.block_first_count <= 2:
            self.block_first_count = self.block_first_count + 1
            return math.ceil((self.maxbudget - 150) / 3)

        if current_artist == second_artist:
            return math.ceil(25)

        return 0


    def second_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known."""

        assets = standings[mybidderid]
        budget = assets["money"]

        # Bid highly to prevent others from getting the first painting
        if rd == 0:
            self.first_painting = itemsinauction[0]
            return 865

        if rd >= 1 and self.second_painting == "" and self.first_painting != itemsinauction[rd]:
            if self.first_painting != itemsinauction[rd]:
                self.second_painting = itemsinauction[rd]

        # Bid consistently 23 for the second paining that appeared in the auction.
        if self.second_painting == itemsinauction[rd]:
            return 23

        # If any set is almost completed, then buy the remaining painting to finish the set. Bid the whole remaining budget.
        if self._almost_complete_set(assets) != False:
            _artist = self._almost_complete_set(assets)
            if itemsinauction[rd] == _artist:
                return budget

        # Bid lowly and get non-sought after paintings cheaply
        return 2

    def third_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 3: Highest total value wins, highest bidder pays own bid, auction order known."""

        # The target decimal of how much of the total valuation should be targeted by the bot.
        # Lower the number, the more aggressive the bot is. It ranges between 0 to 1.
        AIM_DECIMAL = 1 / numberbidders + 0.1
        if (numberbidders > 10):
            AIM_DECIMAL = 1 / numberbidders + 0.05
        elif numberbidders > 15:
            AIM_DECIMAL = 1 / numberbidders + 0.02
        else:
            AIM_DECIMAL = 1 / numberbidders + 0.1

        # Budget left
        assets = standings[mybidderid]
        budget = assets['money']

        self.total_value_left = self._total_value_of_paintings(values, itemsinauction)
        if self.total_value_of_paintings < self.total_value_left:
            self.total_value_of_paintings = self.total_value_left

        # Targetting a fraction of the total valuations to win
        aim_pts = self.total_value_of_paintings * AIM_DECIMAL

        current_pts = self._total_value_of_my_paintings(values, assets)

        # Of the remaining target valuation, how much should each valuation convert to the money left so it's spread equally.
        aim_pts_left = aim_pts - current_pts
        # Used to prevent division by 0
        if aim_pts == 0: aim_pts = 1
        if aim_pts_left == 0: aim_pts_left = 1

        overall_cost_per_pts = self.maxbudget / aim_pts
        cost_per_pts_left = (budget) / (aim_pts_left)

        current_artist = itemsinauction[rd]
        value_of_current_artist = values[current_artist]
        points_for_current_artist = value_of_current_artist * cost_per_pts_left
        max_pts_for_current_painting = math.ceil(points_for_current_artist)

        return max_pts_for_current_painting


    def fourth_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known."""

        # Constant added onto the optimal strategy declared in auction 3
        ALPHA = 2

        AIM_DECIMAL = 1 / numberbidders + 0.1
        if (numberbidders > 10):
            AIM_DECIMAL = 1 / numberbidders + 0.05
        elif numberbidders > 15:
            AIM_DECIMAL = 1 / numberbidders + 0.02
        else:
            AIM_DECIMAL = 1 / numberbidders + 0.1

        # Budget left
        assets = standings[mybidderid]
        budget = assets['money']

        self.total_value_left = self._total_value_of_paintings(values, itemsinauction)
        if self.total_value_of_paintings < self.total_value_left:
            self.total_value_of_paintings = self.total_value_left

        aim_pts = self.total_value_of_paintings * AIM_DECIMAL

        current_pts = self._total_value_of_my_paintings(values, assets)

        aim_pts_left = aim_pts - current_pts
        # Used to prevent division by 0
        if aim_pts == 0: aim_pts = 1
        if aim_pts_left == 0: aim_pts_left = 1

        overall_cost_per_pts = self.maxbudget / aim_pts
        cost_per_pts_left = (budget) / (aim_pts_left)

        current_artist = itemsinauction[rd]
        value_of_current_artist = values[current_artist]
        points_for_current_artist = value_of_current_artist * cost_per_pts_left
        max_pts_for_current_painting = math.ceil(points_for_current_artist)

        # calculate the optimal bid as shown in three and then add a small Alpha variable as this is a second price auction
        return max_pts_for_current_painting + ALPHA


    def first_n_artists(self, artists, paintings, n, pos):

        _top_artists_order = []

        _artist_count = {}
        _artists_arr = list(artists.keys())
        _paintings_arr = paintings

        for i in range(len(_artists_arr)):
            _artist_count[_artists_arr[i]] = 0

        for i in range(len(_paintings_arr)):
            _artist = _paintings_arr[i]

            _artist_count[_artist] = _artist_count[_artist] + 1

            _limit_reached = self._limit_is_reached(_artist_count, n)

            if _limit_reached is not False:
                _top_artists_order.append(_limit_reached)

                if pos == 1:
                    return _limit_reached
                else:
                    # Remove the character from the original array and recurse
                    _removed_char_arr = self._remove_elem_from_arr(_paintings_arr, _limit_reached)
                    _artists_copied = copy.deepcopy(artists)
                    del (_artists_copied[_limit_reached])
                    return self.first_n_artists(_artists_copied, _removed_char_arr, n, pos - 1)


    def _remove_elem_from_arr(self, arr, elem):

        copied_arr = copy.deepcopy(arr)

        count = 0
        for i in range(len(arr)):
            if elem == arr[i]:
                count = count + 1

        for i in range(count):
            copied_arr.remove(elem)

        return copied_arr


    def _limit_is_reached(self, artist_count, n):
        for key, value in artist_count.items():

            if value >= n:
                return key

        return False


    def _total_value_of_my_paintings(self, _values, _paintings):

        _total_value = 0
        MONEY = "money"

        _paintings = copy.deepcopy(_paintings)

        if MONEY in _paintings:
            del (_paintings[MONEY])

        for key, value in _paintings.items():
            _total_value = _total_value + _values[key] * value

        return _total_value


    def _total_value_of_paintings(self, _values, _paintings):

        _total_value = 0

        for i in range(len(_paintings)):
            _total_value = _total_value + _values[_paintings[i]]

        return _total_value


    def _almost_complete_set(self, _assets):

        _copied = copy.deepcopy(_assets)

        _ret = False
        for key, value in _copied.items():
            if value != "money" and value == 4:
                return key

        return _ret
