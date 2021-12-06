#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <dirent.h>
#include <sys/time.h>

#define MAX(a, b) ((a > b) ? (a) : (b))
#define MIN(a, b) ((a < b) ? (a) : (b))

#define LINE_SIZE 9
#define GAME_SIZE 81
#define BASE_POWER 2

struct place {
	int coordinates[3];
	int list_index;
	int options[9];
	struct place *next;
};

long interactions = 0;

/*
	look in the lines, columns and blocks for direct answers
*/
int calculate_alternatives(int *alternatives, int number){
	int integer_part, count;
	double expoent;
	
	count = 0;

	while (number > 0){
		expoent = log2f(number);
		integer_part = (int) expoent;
		number = number - pow(BASE_POWER, integer_part);
		alternatives[count] = integer_part+1;
		count++;		
	}
	
	while (count < LINE_SIZE){
		alternatives[count] = 0;
		count++;
	}
}

int find_unique_number(struct place *position, int line, int column, int block){
	int combined_numbers, full_line, result;
	double expoent, reminder, dividend;
		
	if (MIN(MIN(line,column),block) < 0 || MAX(MAX(line,column),block) > 511)	return -1;	
	
	dividend = 2.0;
	full_line = 0b111111111;	
	combined_numbers = (line | column | block) ^ full_line;
	expoent = log2f(combined_numbers);
	reminder = modf(expoent, &dividend);
	
	if (combined_numbers == 0) return 0;

	if (reminder != 0){
		calculate_alternatives(position->options, combined_numbers);
		return -1;
	}
	
	return (int) expoent+1;
}

/* 
	convert a list of numbers in the string format to a list of integers
*/
int generate_integer_array(char *array_to_convert, int *return_integers){
	int current_number, loop_index, return_index;
	
	current_number = 0;
	return_index = 0;
	
	for (loop_index=0; loop_index < strlen(array_to_convert); loop_index++)
		return_integers[loop_index] = *(array_to_convert + loop_index) - '0';	
	
	return 0;
}

/*
	Take a list of indexes and turn their bits on, generating an
	integer as a result
*/
int generate_bit_line(int *itens_to_convert, int number_of_itens){
	int count, return_value;
	
	return_value = 0;
	
	for (count=0; count<number_of_itens; count++)
		if (itens_to_convert > 0)
			return_value += pow(BASE_POWER, itens_to_convert[count]-1);
	
	return return_value;
}

/*
	return the numbers of a specific line
*/
int get_line(int *all_data, int line, int *return_line){
	int count, displacement;

	displacement = LINE_SIZE*(line-1);
	
	for (count=0; count<9; count ++)
		return_line[count] = all_data[count + displacement];
	
	return 0;
}

/*
	return the numbers of a specific column
*/
int get_column(int *all_data, int column, int *return_line){
	int count, displacement;
		
	for (count=0; count<9; count ++){
		displacement = LINE_SIZE*count;
		return_line[count] = all_data[displacement + column - 1];
	}
	
	return 0;
}

/*
	return the numbers of a specific block
*/
int get_group(int *all_data, int group, int *return_line){
	int vertical_displacement, horizontal_displacement, check_displacement;
	int y_displacement, x_displacement, count_line, count_column, count_total;
	
	vertical_displacement = 0;	
	for (check_displacement = group; check_displacement > 3; check_displacement -= 3)
		vertical_displacement += 3;
	
	horizontal_displacement = 3 * (check_displacement - 1);	
	count_total = 0;
	for (count_line=0;count_line<3;count_line++){
		x_displacement = horizontal_displacement+count_line;
		for(count_column=0;count_column<3;count_column++){
			y_displacement = (LINE_SIZE*vertical_displacement + (count_column*LINE_SIZE));
			return_line[count_total] = all_data[x_displacement + y_displacement];
			count_total++;
		}
	}
	
	return 0;
}

/*
	from a sudoku game, return a string line with the numbers of
	the line, the column or the block specified. The format of the
	position is 900 return the 9th line, 050 return the 5th column.
*/
int get_integer_line(int *all_data, int position, int *line){
	if (position < 10)
		get_line(all_data, position, line);		
	 else if(position < 100)
		get_column(all_data, (position/10), line);
	 else 
		get_group(all_data, (position/100), line);
	
	return 0;	
}

/*
	read a sudoku game from a specified file and transform it into
	a char list of digits
*/
char* get_game_from_file(char file_name[], char *game){
	FILE *sudoku_game;
	char number;
	int count;
	
	sudoku_game = fopen(file_name,"r");

	if (sudoku_game == NULL){
		printf("Erro ao abrir o arquivo");
		return '\0';
	}
	
	for (count = 0; count < GAME_SIZE; count++){
		number = '\0';
		while(number < '0' || number > '9')	fscanf(sudoku_game,"%c", &number);
		*(game + count) = (char) number;
	}
	*(game + count) = '\0';	
	
	fclose(sudoku_game);
	
	return game;
}

/*
	Add a new element at to the end of the list
*/
int add_to_list(struct place *list_end, int line, int column, int block, int position){
	struct place *new_place;
	
	if (list_end->next != NULL) return -1;
	
	new_place = (struct place*) malloc(sizeof(struct place));
	
	new_place->coordinates[0] = line;
	new_place->coordinates[1] = column;
	new_place->coordinates[2] = block;
	new_place->list_index = position;
	new_place->next = NULL;
	list_end->next = new_place;
	
	return 0;	
}

/*
	check every game position if there is a unique replacement
	to be done.
*/
int find_open_places(int *game, struct place *list){
	int count, line, column, block, block_displacement;
	struct place *last_element;
	
	last_element = (struct place*) malloc(sizeof(struct place));
	last_element = list;
	
	while (last_element->next != NULL) last_element = last_element->next;
	
	block_displacement = 0;
	line = 1;
	column = 0;
	block = 1;
	for (count = 0; count < GAME_SIZE; count ++){
		column++;
		if (column > LINE_SIZE){
			column = 1;
			line++;
			block = 1;		
		}
		if (game[count] == 0){
			add_to_list(last_element, line, column, (block+block_displacement), count);
			last_element = last_element->next;
		}
		if (column%3 == 0) block++;
		if ((count+1)%27 == 0) block_displacement += 3;
	}
	
	*list = *(list->next);
	
	return 0;
}

/*
	look at a specific open posisiont and verify it there
	is a direct to to fill the place.	
*/
int verify_place(int *game, struct place *place_to_look){
	int count, multiplier, answer;
	int array_line[LINE_SIZE], bit_lines[3];
	
	if (place_to_look == NULL)	return -1;
	
	multiplier = 1;
	for (count = 0; count < 3; count++){
		get_integer_line(game, (place_to_look->coordinates[count] * multiplier), array_line);
		bit_lines[count] = generate_bit_line(array_line, LINE_SIZE);
		multiplier = multiplier * 10;
	}
	 
	return find_unique_number(place_to_look, bit_lines[0], bit_lines[1], bit_lines[2]);
}

/*
	try the easy path to solve the puzzle
*/
int try_simple_moves(struct place *list, int *game){
	char changed_element;
	int answer, count, moves, last_move;
	struct place *current, *previous;
	
	current = (struct place*) malloc(sizeof(struct place));
	previous = (struct place*) malloc(sizeof(struct place));

	changed_element = '1';
	moves = 0;
	
	while(changed_element == '1'){
		changed_element = '0';
		current = list;
		previous = NULL;
		while(current != NULL){
			answer = verify_place(game, current);
			if (answer > 0){
				game[current->list_index] = answer;
				if (previous != NULL)
					previous->next = current->next;
				else 
					list->list_index = -1;
				changed_element = '1';
				current = NULL;
				moves++;
			}
			previous = current;
			if (current != NULL)
				current = current->next;
		}
	}
	while(list->next != NULL && list->list_index == -1)
		*list = *list->next;

	return moves;
}
/*
	looks at the game to see if there are still moves to be done.
*/
int count_zeros(int *game, int number_of_itens){
	int count, zeros_count;

	zeros_count = 0;
	for (count = 0; count < number_of_itens; count++){
		if (game[count] == 0)
			zeros_count++;
	}
	
	return zeros_count;
}

/*
	print the game at the screen in a proper way
*/

void print_game(int *game){
	int count;
	system("clear");
	printf("\n");
	for (count = 0; count < GAME_SIZE; count++){
		if (count%9==0 && count > 0)
			printf("\n");
		printf(" %d ", game[count]);
	}
	printf("\n");
}

/*
	verify if a move can be done based on the current game.
*/
int check_conflict(int *game, struct place *place_to_look, int index){
	short count, multiplier;
	int bit_line, bit_move, array_line[LINE_SIZE];
	
	bit_move = pow(BASE_POWER, place_to_look->options[index]-1);
	multiplier = 1;
	for (count = 0; count < 3; count++){
		get_integer_line(game, (place_to_look->coordinates[count] * multiplier), array_line);
		bit_line = generate_bit_line(array_line, LINE_SIZE);
		if (bit_line & bit_move) return 0;
		multiplier = multiplier * 10;
	}
	
	return 1;
}

/*
	backtraking function
*/
int backtraking(struct place *list, int *game){
	int count;
	interactions++;
	if (list == NULL) return 1;
	
	for (count = 0; count < LINE_SIZE && list->options[count] != 0; count++){
		if (check_conflict(game, list, count) != 0){
			game[list->list_index] = list->options[count];
			if (backtraking(list->next, game) == 1) return 1;
			game[list->list_index] = 0;
		}
	}
	game[list->list_index] = 0;
	return 0;
}

int main(int argc, char *argv[])
{
	char game[GAME_SIZE+1], option[1];
	int game_integer[GAME_SIZE], count;
	int moves_done, zeros_remaining;
	struct place *list;
	struct timeval start_clock, end_clock;
	double times_difference;
	
	
	if (argc != 2){
		printf("Usage: ./%s <game>\n", argv[0]);
		return 0;
	}	
	
	gettimeofday(&start_clock, NULL);
	list = (struct place*) malloc(sizeof(struct place));
		
	list->next = NULL;
	
	get_game_from_file(argv[1], game);	
	generate_integer_array(game, game_integer);	
	find_open_places(game_integer, list);
	moves_done = try_simple_moves(list, game_integer);
	zeros_remaining = count_zeros(game_integer, GAME_SIZE);	
	
	if (zeros_remaining > 0) backtraking(list, game_integer);
		
	gettimeofday(&end_clock, NULL);
	times_difference = (double) (end_clock.tv_usec - start_clock.tv_usec) / 1000000 + (end_clock.tv_sec - start_clock.tv_sec);
	
	print_game(game_integer);
	printf("\n\nThe running time was: %lf seconds \n", times_difference);
	printf("The game %s have %d moves done without try and error.\n", argv[1], moves_done);
	printf("%d moves were done by brute force, in a total of %d interactions!\n", zeros_remaining, interactions);
	
	return 0;	
}